# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

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

    mobile/          Fennec builds
      candidates/    beta, rc, and release builds
      nightly/       nightly builds


This traverses the entire tree every time. If there are missing builds, it will
pick them up the next time it runs. There's no maintained state for this job
and it always backfills.

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

The first run will collect everything. After that, it'll skip versions that
are before the latest major version in the database minus 3. For example, if
there are builds in the database for 63, then it'll only scrape information
for 60 and higher for that product.

You can run this in a local development environment like this::

    docker-compose run app shell ./socorro-cmd crontabber \
        --job=archivescraper --crontabber.class-ArchiveScraperCronApp.verbose


The "verbose" argument will cause it to log helpful information for diagnosing
issues.

"""

from __future__ import print_function

import json

from configman import Namespace
import psycopg2
from pyquery import PyQuery as pq
from six.moves.urllib.parse import urljoin

from socorro.cron.base import BaseCronApp
from socorro.cron.mixins import using_postgres
from socorro.lib.requestslib import session_with_retries


# Substrings that indicate the thing is not a platform we want to traverse
NON_PLATFORM_SUBSTRINGS = [
    'beetmover',
    'contrib',
    'funnelcake',
    'jsshell',
    'logs',
    'mar-tools',
    'partner-repacks',
    'source',
    'update'
]


@using_postgres()
class ArchiveScraperCronApp(BaseCronApp):
    app_name = 'archivescraper'
    app_description = 'scraper for archive.mozilla.org for release info'
    app_version = '1.0'

    required_config = Namespace()
    required_config.add_option(
        'base_url',
        default='https://archive.mozilla.org/pub/',
        doc='base url to use for fetching builds'
    )
    required_config.add_option(
        'verbose',
        default=False,
        doc='print verbose information about spidering'
    )

    def __init__(self, *args, **kwargs):
        super(ArchiveScraperCronApp, self).__init__(*args, **kwargs)
        # NOTE(willkg): If archive.mozilla.org is timing out after 5 seconds,
        # then it has issues and we should try again some other time
        self.session = session_with_retries(default_timeout=5.0)
        self.successful_inserts = 0

    def _get_max_major_version(self, connection, product_name):
        cursor = connection.cursor()
        sql = """
        SELECT max(major_version)
        FROM crashstats_productversion
        WHERE product_name = %s
        """
        params = (product_name,)
        cursor.execute(sql, params)
        data = cursor.fetchall()
        if data:
            return data[0][0]
        return None

    def get_max_major_version(self, product_name):
        """Retrieves the max major version for this product

        :arg str product_name: the name of the product

        :returns: maximum major version as an int or None

        """
        return self.database_transaction_executor(self._get_max_major_version, product_name)

    def _insert_build_transaction(self, connection, params):
        if self.config.verbose:
            self.config.logger.info('INSERTING: %s' % list(sorted(params.items())))
        cursor = connection.cursor()
        sql = """
        INSERT INTO crashstats_productversion (
            product_name, release_channel, major_version, release_version,
            version_string, build_id, archive_url
        )
        VALUES (
            %(product_name)s, %(release_channel)s, %(major_version)s, %(release_version)s,
            %(version_string)s, %(build_id)s, %(archive_url)s
        )
        """
        try:
            cursor.execute(sql, params)
            self.successful_inserts += 1
        except psycopg2.IntegrityError:
            # If it's an IntegrityError, we already have it and everything is fine
            pass
        except psycopg2.Error:
            self.config.logger.exception('failed to insert')

    def insert_build(self, product_name, release_channel, major_version, release_version,
                     version_string, build_id, archive_url):
        data = {
            'product_name': product_name,
            'release_channel': release_channel,
            'major_version': major_version,
            'release_version': release_version,
            'version_string': version_string,
            'build_id': build_id,
            'archive_url': archive_url
        }
        self.database_transaction_executor(self._insert_build_transaction, data)

    def get_links(self, content):
        """Retrieves valid links on the page

        This skips links that are missing an href or text or are for "." or "..".

        :arg str content: the content of the page

        :returns: list of dicts with "path" and "text" keys

        """
        d = pq(content)
        return [
            {
                'path': elem.get('href'),
                'text': elem.text
            }
            for elem in d('a')
            if elem.get('href') and elem.text and elem.text not in ('.', '..')
        ]

    def download(self, url_path):
        """Retrieves contents for a page

        This will log an error and return "" when it gets a non-200 status code. This
        allows scraping to continue and at least get something.

        :arg str url_path: the path to retrieve

        :returns: contents of the page or ""

        """
        url = urljoin(self.config.base_url, url_path)
        if self.config.verbose:
            self.config.logger.info('downloading: %s', url)
        resp = self.session.get(url)
        if resp.status_code != 200:
            if self.config.verbose:
                # Most of these are 404s because we guessed a url wrong which is fine
                self.config.logger.warning('Bad status: %s: %s', url, resp.status_code)
            return ''

        return resp.content

    def get_json_links(self, path):
        """Traverses a directory of platforms and returns links to build info files

        :arg str path: the path to start at

        :returns: list of urls

        """
        build_contents = self.download(path)
        directory_links = [
            link['path'] for link in self.get_links(build_contents)
            if link['text'].endswith('/')
        ]

        all_json_links = []
        for directory_link in directory_links:
            # Skip known unhelpful directories
            if any([(bad_dir in directory_link) for bad_dir in NON_PLATFORM_SUBSTRINGS]):
                continue

            # We don't need to track all locales, so we only look at en-US and get
            # the information from the first platform that we check that has it
            locale_contents = self.download(directory_link + 'en-US/')
            if not locale_contents:
                continue

            json_links = [
                link['path'] for link in self.get_links(locale_contents)
                if (link['path'].endswith('.json') and
                    'mozinfo' not in link['path'] and
                    'test_packages' not in link['path'])
            ]

            # If there's a buildhub.json link, return that
            buildhub_links = [
                link for link in json_links if link.endswith('buildhub.json')
            ]
            if buildhub_links:
                all_json_links.append(buildhub_links[0])
            elif json_links:
                # If there isn't a buildhub link, return the first json file we found
                all_json_links.append(json_links[0])

        return all_json_links

    def scrape_candidates(self, product_name, url_path):
        """Scrape the candidates/ directory for beta, release candidate, and final releases"""
        major_version = self.get_max_major_version(product_name)

        content = self.download(url_path)
        version_links = [
            link for link in self.get_links(content)
            if link['text'][0].isdigit()
        ]

        # If we've got a major_version, then we only want to scrape data for versions
        # greater than (major_version - 3)
        if major_version:
            major_version_minus_3 = major_version - 3
            self.config.logger.info('Skipping anything before %s', major_version_minus_3)
            version_links = [
                link for link in version_links
                # "63.0b7-candidates/" -> 63
                if int(link['text'].split('.')[0]) >= major_version_minus_3
            ]

        # For each version in the candidates/ directory, we traverse the tree finding
        # the first build info file we can find
        for link in version_links:
            content = self.download(link['path'])
            build_links = [
                link for link in self.get_links(content)
                if link['text'].startswith('build')
            ]

            #  /pub/PRODUCT/candidates/VERSION/...   # noqa
            # 0/1  / 2     /3         /4
            version_root = link['path'].split('/')[4]
            version_root = version_root.replace('-candidates', '')

            for i, build_link in enumerate(build_links):
                # Get the json file somewhere in this part of the tree
                json_links = self.get_json_links(build_link['path'])
                if not json_links:
                    self.config.logger.warning(
                        'could not find json files in: %s', build_link['path']
                    )
                    continue

                for json_link in json_links:
                    json_file = self.download(json_link)
                    data = json.loads(json_file)

                    if 'buildhub' in json_link:
                        # We have a buildhub.json file to use, so we use that
                        # structure
                        data = {
                            'product_name': product_name,
                            'release_channel': data['target']['channel'],
                            'major_version': int(data['target']['version'].split('.')[0]),
                            'release_version': data['target']['version'],
                            'build_id': data['build']['id'],
                            'archive_url': urljoin(self.config.base_url, json_link)
                        }

                    else:
                        # We have the older build info file format, so we use that
                        # structure
                        data = {
                            'product_name': product_name,
                            'release_channel': data['moz_update_channel'],
                            'major_version': int(data['moz_app_version'].split('.')[0]),
                            'release_version': data['moz_app_version'],
                            'build_id': data['buildid'],
                            'archive_url': urljoin(self.config.base_url, json_link)
                        }

                    # The build link text is something like "build1/" and we
                    # want just the number part, so we drop "build" and the "/"
                    rc_version_string = version_root + 'rc' + build_link['text'][5:-1]

                    # Whether or not this is the final build for a set of builds; for
                    # example for [build1, build2, build3] the final build is build3
                    final_build = (i + 1 == len(build_links))

                    if final_build:
                        if data['release_channel'] == 'release':
                            # If this is a final build for a major release, then we want to
                            # insert two entries--one for the last rc in the beta channel
                            # and one for the final release in the release channel. This
                            # makes it possible to look up version strings in one request.

                            # Insert the rc beta build
                            data['release_channel'] = 'beta'
                            data['version_string'] = rc_version_string
                            self.insert_build(**data)

                            # Insert the final release build
                            data['version_string'] = version_root
                            data['release_channel'] = 'release'
                            self.insert_build(**data)

                        else:
                            # This is the final build for a beta release, so we insert both
                            # an rc as well as a final as betas
                            data['version_string'] = version_root
                            self.insert_build(**data)

                            data['version_string'] = rc_version_string
                            self.insert_build(**data)

                    else:
                        if data['release_channel'] == 'release':
                            # This is a release channel build, but it's not a final build,
                            # so insert it as an rc beta build
                            data['version_string'] = rc_version_string
                            data['release_channel'] = 'beta'
                            self.insert_build(**data)

                        else:
                            # Insert the rc beta build
                            data['version_string'] = rc_version_string
                            self.insert_build(**data)

    def run(self):
        # Capture Firefox beta and release builds
        self.scrape_candidates(
            product_name='Firefox',
            url_path='/pub/firefox/candidates/'
        )
        # Pick up DevEdition beta builds for which b1 and b2 are "Firefox builds"
        self.scrape_candidates(
            product_name='DevEdition',
            url_path='/pub/devedition/candidates/'
        )

        # Capture Fennec beta and release builds
        self.scrape_candidates(
            product_name='Fennec',
            url_path='/pub/mobile/candidates/'
        )

        self.config.logger.info('Inserted %s builds.', self.successful_inserts)
