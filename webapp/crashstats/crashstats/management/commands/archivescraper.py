# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
This is a quick-and-dirty scraper for archive.mozilla.org that optimizes on
code maintenance followed by the amount of work this needs to do every time it
runs. It's written with the assumption that it will be temporary.

Rough directory structure::

  pub/
    firefox/         Firefox builds
      candidates/    beta, rc, release, and esr builds
      nightly/       nightly builds

    devedition/      DevEdition (aka Firefox aurora)
      candidates/    beta builds for Firefox b1 and b2

    thunderbird/
      candidates/    beta, rc, release, and esr builds
      nightly/       nightly builds


This job only looks for build information for the en-US locale for the first
platform in a build directory that has build information. Once it's found some
build information, it moves on to the next version.

This captures the information required to convert a release version into a
version string. Incoming crash reports have a release version like "63.0", but
it's really something like "63.0b4" and having the actual version is important
for analysis.

Since we only do this conversion for aurora, beta, and release versions, we
don't scrape nightly builds.

Data is stored in the crashstats_productversion table which is managed by the
webapp (Django).

The record includes the full url of the build file archivescraper pulled the
information from. This will help for diagnosis of issues in the future.

The first run will collect everything. After that, it'll skip versions that are
before the latest major version in the database minus 4. For example, if there
are builds in the database for 63, then it'll only scrape information for 59
and higher for that product. It will collect anything with "esr" in the name.
If there are missing builds, it will pick them up the next time it runs.

You can run this in a local development environment like this::

    $ ./webapp/manage.py archivescraper

See ``--help`` for arguments.

"""

import concurrent.futures
import copy
from functools import partial
import json
from urllib.parse import urljoin

import more_itertools
from pyquery import PyQuery as pq

from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

from crashstats.crashstats.models import ProductVersion
from socorro.lib.librequests import session_with_retries


# Substrings that indicate the directory is not a platform we want to traverse
NON_PLATFORM_SUBSTRINGS = [
    "beetmover",
    "contrib",
    "funnelcake",
    "jsshell",
    "logs",
    "mar-tools",
    "partner-repacks",
    "source",
    "update",
]


def key_for_build_link(link):
    """Extract build number from build link."""
    # The path is something like "build10/". We want to pull out the
    # integer from that.
    path = link["path"]
    return int("".join([c for c in path if c.isdigit()]))


def get_session():
    """Return a retryable requests session."""
    # NOTE(willkg): If archive.mozilla.org is timing out after 5 seconds, then
    # it has issues and we should try again some other time
    return session_with_retries(default_timeout=5.0)


class Downloader:
    """Downloader class.

    NOTE(willkg): I broke this out because it needs to be serializable so it
    works with concurrant.futures. configman isn't serializable. Once we stop
    using configman, we can merge this again.

    """

    def __init__(self, base_url, num_workers, verbose):
        self.base_url = base_url
        self.num_workers = num_workers
        self.verbose = verbose
        self.msgs = []

    def worker_write(self, msg, verbose=False):
        """Writes to stdout or msgs buffer.

        Use this in workers rather than printing directly to stdout so it can
        be passed to the parent process correctly.

        :arg str msg: the message to write
        :arg bool verbose: whether to write this only if in verbose mode

        """
        if verbose and not self.verbose:
            return

        self.msgs.append(msg)

    def get_links(self, content):
        """Retrieve valid links on the page.

        This ignores links that are missing an href or text or are for "." or
        "..".

        :arg str content: the content of the page

        :returns: list of dicts with "path" and "text" keys

        """
        d = pq(content)
        return [
            {"path": elem.get("href"), "text": elem.text}
            for elem in d("a")
            if elem.get("href") and elem.text and elem.text not in (".", "..")
        ]

    def download(self, url_path):
        """Retrieve contents for a page.

        This will log an error and return "" when it gets a non-200 status code. This
        allows scraping to continue and at least get something.

        :arg str url_path: the path to retrieve

        :returns: contents of the page or ""

        """
        url = urljoin(self.base_url, url_path)
        self.worker_write("downloading: %s" % url, verbose=True)
        resp = get_session().get(url)
        if resp.status_code != 200:
            if self.verbose:
                # Most of these are 404s because we guessed a url wrong which is fine
                self.worker_write("bad status: %s: %s" % (url, resp.status_code))
            return ""

        return resp.content

    def get_json_links(self, path):
        """Traverse directory of platforms and returns links to build info files.

        :arg str path: the path to start at

        :returns: list of urls

        """
        build_contents = self.download(path)
        directory_links = [
            link["path"]
            for link in self.get_links(build_contents)
            if link["text"].endswith("/")
        ]

        all_json_links = []
        for directory_link in directory_links:
            # Skip known unhelpful directories
            if any(
                [(bad_dir in directory_link) for bad_dir in NON_PLATFORM_SUBSTRINGS]
            ):
                continue

            # We don't need to track all locales, so we only look at en-US and get
            # the information from the first platform that we check that has it
            locale_contents = self.download(directory_link + "en-US/")
            if not locale_contents:
                continue

            json_links = [
                link["path"]
                for link in self.get_links(locale_contents)
                if (
                    link["path"].endswith(".json")
                    and "mozinfo" not in link["path"]
                    and "test_packages" not in link["path"]
                )
            ]

            # If there's a buildhub.json link, return that
            buildhub_links = [
                link for link in json_links if link.endswith("buildhub.json")
            ]
            if buildhub_links:
                all_json_links.append(buildhub_links[0])
            elif json_links:
                # If there isn't a buildhub link, return the first json file we found
                all_json_links.append(json_links[0])

        return all_json_links

    def scrape_candidate_version(self, link, product_name, final_releases):
        """Traverse candidates/VERSION/ tree returning list of build info."""
        self.msgs = []

        content = self.download(link["path"])
        build_links = [
            link for link in self.get_links(content) if link["text"].startswith("build")
        ]

        #  /pub/PRODUCT/candidates/VERSION/...   # noqa
        # 0/1  / 2     /3         /4
        version_root = link["path"].split("/")[4]
        version_root = version_root.replace("-candidates", "")

        # Was there a final release of this series? If so, then we can do
        # final build versions
        is_final_release = version_root in final_releases

        # Sort the builds by the build number so they're in numeric order because
        # the last one is possibly a final build
        build_links.sort(key=key_for_build_link)

        build_data = []

        for i, build_link in enumerate(build_links):
            # Get all the json files with build information in them for all the
            # platforms that have them
            json_links = self.get_json_links(build_link["path"])
            if not json_links:
                self.worker_write(
                    "could not find json files in: %s" % build_link["path"]
                )
                continue

            # Go through all the links we acquired by traversing all the platform
            # directories
            for json_link in json_links:
                json_file = self.download(json_link)
                try:
                    data = json.loads(json_file)
                except json.decoder.JSONDecodeError:
                    self.worker_write(f"not valid json: {json_link}")
                    continue

                if "buildhub" in json_link:
                    # We have a buildhub.json file to use, so we use that
                    # structure
                    data = {
                        "product_name": product_name,
                        "release_channel": data["target"]["channel"],
                        "major_version": int(data["target"]["version"].split(".")[0]),
                        "release_version": data["target"]["version"],
                        "build_id": data["build"]["id"],
                        "archive_url": urljoin(self.base_url, json_link),
                    }

                else:
                    # We have the older build info file format, so we use that
                    # structure
                    data = {
                        "product_name": product_name,
                        "release_channel": data["moz_update_channel"],
                        "major_version": int(data["moz_app_version"].split(".")[0]),
                        "release_version": data["moz_app_version"],
                        "build_id": data["buildid"],
                        "archive_url": urljoin(self.base_url, json_link),
                    }

                # The build link text is something like "build1/" and we
                # want just the number part, so we drop "build" and the "/"
                rc_version_string = version_root + "rc" + build_link["text"][5:-1]

                # Whether or not this is the final build for a set of builds; for
                # example for [build1, build2, build3] the last build is build3
                # and if there was a release in the /pub/PRODUCT/releases/ directory
                # then this is a final build
                final_build = (i + 1 == len(build_links)) and is_final_release

                if final_build:
                    if data["release_channel"] == "release":
                        # If this is a final build for a major release, then we want to
                        # insert two entries--one for the last rc in the beta channel
                        # and one for the final release in the release channel. This
                        # makes it possible to look up version strings for beta and rc
                        # builds in one request.

                        # Insert the rc beta build
                        data["release_channel"] = "beta"
                        data["version_string"] = rc_version_string
                        build_data.append(data)

                        # Insert the final release build
                        second_data = copy.deepcopy(data)
                        second_data["version_string"] = version_root
                        second_data["release_channel"] = "release"
                        build_data.append(second_data)

                    else:
                        # This is the final build for a beta release, so we insert both
                        # an rc as well as a final as betas
                        data["version_string"] = version_root
                        build_data.append(data)

                        second_data = copy.deepcopy(data)
                        second_data["version_string"] = rc_version_string
                        build_data.append(second_data)

                else:
                    if data["release_channel"] == "release":
                        # This is a release channel build, but it's not a final build,
                        # so insert it as an rc beta build
                        data["version_string"] = rc_version_string
                        data["release_channel"] = "beta"
                        build_data.append(data)

                    else:
                        # Insert the rc beta build
                        data["version_string"] = rc_version_string
                        build_data.append(data)

        return build_data, self.msgs

    def scrape_candidates(self, product_name, archive_directory, major_version, stdout):
        """Scrape the candidates/ directory for beta, release candidate, and final releases."""
        url_path = "/pub/%s/candidates/" % archive_directory
        stdout.write("scrape_candidates working on %s" % url_path)

        # First, let's look at /pub/PRODUCT/releases/ so we know what final
        # builds have been released
        release_path = "/pub/%s/releases/" % archive_directory
        release_path_content = self.download(release_path)

        # Get the final release version numbers, so something like "64.0b8/" -> "64.0b8"
        final_releases = [
            link["text"].rstrip("/")
            for link in self.get_links(release_path_content)
            if link["text"][0].isdigit()
        ]

        content = self.download(url_path)
        version_links = [
            link for link in self.get_links(content) if link["text"][0].isdigit()
        ]

        # If we've got a major_version, then we only want to scrape data for versions
        # greater than (major_version - 4) and esr builds
        if major_version:
            major_version_minus_4 = major_version - 4
            stdout.write(
                "skipping anything before %s and not esr (%s)"
                % (major_version_minus_4, product_name)
            )
            version_links = [
                link
                for link in version_links
                if (
                    # "63.0b7-candidates/" -> 63
                    int(link["text"].split(".")[0]) >= major_version_minus_4
                    or "esr" in link["text"]
                )
            ]

        scrape = partial(
            self.scrape_candidate_version,
            product_name=product_name,
            final_releases=final_releases,
        )

        if self.num_workers == 1:
            results = map(scrape, version_links)

        else:
            with concurrent.futures.ProcessPoolExecutor(
                max_workers=self.num_workers
            ) as executor:
                results = executor.map(scrape, version_links, timeout=300)

        results = list(results)
        # Convert [(build_data, msgs), (build_data, msgs), ...] into
        # build_data and msgs
        if results:
            build_data, msgs = more_itertools.unzip(results)
        else:
            build_data, msgs = [], []

        # Print all the msgs to stdout
        for msg_group in msgs:
            for msg in msg_group:
                stdout.write("worker: %s" % msg)

        # build_data is a list of lists so we flatten that
        return list(more_itertools.flatten(build_data))


class Command(BaseCommand):
    help = "Scrape archive.mozilla.org for productversion information."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-url",
            default="https://archive.mozilla.org/pub/",
            help="base url to use for fetching builds",
        )
        parser.add_argument(
            "--num-workers",
            default=20,
            type=int,
            help="Number of concurrent workers for downloading; set to 1 for single process",
        )

    def get_max_major_version(self, product_name):
        """Retrieve the max major version for this product.

        :arg str product_name: the name of the product

        :returns: maximum major version as an int or None

        """
        pv = ProductVersion.objects.order_by("-major_version").first()
        if pv is not None:
            return pv.major_version
        return None

    def insert_build(
        self,
        product_name,
        release_channel,
        major_version,
        release_version,
        version_string,
        build_id,
        archive_url,
        verbose,
    ):
        """Insert a new build into the crashstats_productversion table."""
        params = {
            "product_name": product_name,
            "release_channel": release_channel,
            "major_version": major_version,
            "release_version": release_version,
            "version_string": version_string,
            "build_id": build_id,
            "archive_url": archive_url,
        }
        try:
            ProductVersion.objects.create(**params)
            if verbose:
                self.stdout.write("INSERTING: %s" % list(sorted(params.items())))
            return True

        except IntegrityError as ie:
            if "violates unique constraint" in str(ie):
                # If there's an IntegrityError, it's because one already exists.
                # That's fine, so let's skip it.
                pass
            else:
                raise

    def scrape_and_insert_build_info(
        self, base_url, num_workers, verbose, product_name, archive_directory
    ):
        """Scrape and insert build info for a specific product/directory."""
        downloader = Downloader(
            base_url=base_url, num_workers=num_workers, verbose=verbose
        )
        major_version = self.get_max_major_version(product_name)
        build_data = downloader.scrape_candidates(
            product_name=product_name,
            archive_directory=archive_directory,
            major_version=major_version,
            stdout=self.stdout,
        )
        total_builds = 0
        num_builds = 0
        for item in build_data:
            total_builds += 1
            if self.insert_build(verbose=verbose, **item):
                num_builds += 1
        self.stdout.write(
            "found %s builds; inserted %s builds" % (total_builds, num_builds)
        )
        return num_builds

    def handle(self, **options):
        num_workers = options["num_workers"]
        base_url = options["base_url"]
        verbose = options["verbosity"] > 1

        # Capture Firefox beta and release builds
        self.scrape_and_insert_build_info(
            base_url=base_url,
            num_workers=num_workers,
            verbose=verbose,
            product_name="Firefox",
            archive_directory="firefox",
        )

        # Capture Thunderbird beta and release builds
        self.scrape_and_insert_build_info(
            base_url=base_url,
            num_workers=num_workers,
            verbose=verbose,
            product_name="Thunderbird",
            archive_directory="thunderbird",
        )

        # Pick up DevEdition beta builds for which b1 and b2 are "Firefox builds"
        self.scrape_and_insert_build_info(
            base_url=base_url,
            num_workers=num_workers,
            verbose=verbose,
            product_name="DevEdition",
            archive_directory="devedition",
        )

        self.stdout.write("Done!")
