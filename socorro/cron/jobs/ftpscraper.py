from __future__ import print_function

import datetime
import sys
import re
import os
import json
import urlparse
import fnmatch
import functools

import mock
import lxml.html
import requests
from requests.adapters import HTTPAdapter

from configman import Namespace
from configman.converters import class_converter, str_to_list
from crontabber.base import BaseCronApp
from crontabber.mixins import (
    as_backfill_cron_app,
    with_postgres_transactions
)

from socorro.cron import buildutil

from socorro.app.socorro_app import App
from socorro.lib.datetimeutil import string_to_datetime


def memoize_download(fun):
    cache = {}

    @functools.wraps(fun)
    def inner(self, url):
        if url not in cache:
            cache[url] = fun(self, url)
        return cache[url]

    return inner


class ScrapersMixin(object):
    """
    Mixin that requires to be able to call `self.download(some_url)`
    and `self.skip_json_file(json_url)`.
    """

    def get_links(self, url, starts_with=None, ends_with=None):

        results = []
        content = self.download(url)
        if not content:
            return []

        if not (starts_with or ends_with):
            raise NotImplementedError(
                'get_links requires either `startswith` or `endswith`'
            )

        html = lxml.html.document_fromstring(content)

        path = urlparse.urlparse(url).path

        def url_match(link):
            # The link might be something like "/pub/mobile/nightly/"
            # but we're looking for a path that starts with "nightly".
            # So first we need to remove what's part of the base URL
            # to make a fair comparison.
            if starts_with is not None:
                # If the current URL is http://example.com/some/dir/
                # and the link is /some/dir/mypage/ and the thing
                # we're looking for is "myp" then this should be true
                if link.startswith(path):
                    link = link.replace(path, '')
                return link.startswith(starts_with)
            elif ends_with:
                return link.endswith(ends_with)
            return False

        for _, _, link, _ in html.iterlinks():
            if url_match(link):
                results.append(urlparse.urljoin(url, link))
        return results

    def parse_build_json_file(self, url, nightly=False):
        content = self.download(url)
        if content:
            try:
                kvpairs = json.loads(content)
                kvpairs['repository'] = kvpairs.get('moz_source_repo')
                if kvpairs['repository']:
                    kvpairs['repository'] = kvpairs['repository'].split(
                        '/', -1
                    )[-1]
                kvpairs['build_type'] = kvpairs.get('moz_update_channel')
                kvpairs['buildID'] = kvpairs.get('buildid')

                # bug 1065071 - ignore JSON files that have keys with
                # missing values.
                if None in kvpairs.values():
                    self.config.logger.warning(
                        'warning, unsupported JSON file: %s', url
                    )

                return kvpairs
            # bug 963431 - it is valid to have an empty file
            # due to a quirk in our build system
            except ValueError:
                self.config.logger.warning(
                    'Unable to JSON parse content %r',
                    content,
                    exc_info=True
                )

    def parse_info_file(self, url, nightly=False):
        self.config.logger.debug('Opening %s', url)
        content = self.download(url)
        results = {}
        bad_lines = []
        if not content:
            return results, bad_lines
        contents = content.splitlines()
        if nightly:
            results = {'buildID': contents[0], 'rev': contents[1]}
            if len(contents) > 2:
                results['altrev'] = contents[2]
        elif contents:
            results = {}
            for line in contents:
                if line == '':
                    continue
                try:
                    key, value = line.split('=')
                    results[key] = value
                except ValueError:
                    bad_lines.append(line)

        return results, bad_lines

    def get_json_release(self, candidate_url, dirname):
        version = dirname.split('-candidates')[0]

        builds = self.get_links(candidate_url, starts_with='build')
        if not builds:
            return

        latest_build = builds.pop()
        version_build = os.path.basename(os.path.normpath(latest_build))

        possible_platforms = (
            'linux', 'mac', 'win', 'debug',  # for Firefox
            'android-api-16', 'android-api-15', 'android-x86',  # for mobile
        )

        for platform in possible_platforms:
            platform_urls = self.get_links(
                latest_build,
                starts_with=platform
            )

            for platform_url in platform_urls:
                # We're only interested in going into depper directories.
                # Inside a directory like 'firefox/candidates/45.3.0esr-candidates/build1/'
                # there is likely to be regular files that match the
                # 'possible_platforms' above. Skip those that aren't directories.
                # This means we're much less likely to open URLs like
                # '...45.3.0esr-candidates/build1/en-US/' which'll 404
                if not platform_url.endswith('/'):
                    continue

                platform_local_url = urlparse.urljoin(platform_url, 'en-US/')
                json_files = self.get_links(
                    platform_local_url,
                    ends_with='.json'
                )
                for json_url in json_files:
                    if self.skip_json_file(json_url):
                        continue
                    kvpairs = self.parse_build_json_file(json_url)
                    if not kvpairs:
                        continue
                    kvpairs['version_build'] = version_build
                    yield (platform, version, kvpairs)

    def get_json_nightly(self, nightly_url, dirname):
        json_files = self.get_links(nightly_url, ends_with='.json')
        for url in json_files:
            if self.skip_json_file(url):
                continue
            basename = os.path.basename(url)
            if '.en-US.' in url:
                pv, platform = re.sub('\.json$', '', basename).split('.en-US.')
            elif '.multi.' in url:
                pv, platform = re.sub('\.json$', '', basename).split('.multi.')
            else:
                continue

            version = pv.split('-')[-1]
            repository = []

            for field in dirname.split('-'):
                # Skip until something is not a digit and once we've
                # appended at least one, keep adding.
                if not field.isdigit() or repository:
                    repository.append(field)
            repository = '-'.join(repository).strip('/')

            kvpairs = self.parse_build_json_file(url, nightly=True)

            yield (platform, repository, version, kvpairs)

    def get_release(self, candidate_url):
        builds = self.get_links(candidate_url, starts_with='build')
        if not builds:
            self.config.logger.info('No build dirs in %s', candidate_url)
            return

        latest_build = builds.pop()
        version_build = os.path.basename(os.path.normpath(latest_build))
        info_files = self.get_links(latest_build, ends_with='_info.txt')
        for info_url in info_files:
            kvpairs, bad_lines = self.parse_info_file(info_url)
            # os.path.basename works on URL looking things too
            # and not just file path
            platform = os.path.basename(info_url).split('_info.txt')[0]

            # suppose the `info_url` is something like
            # "https://archive.moz.../40.0.3-candidates/..11_info.txt"
            # then look for the "40.0.3-candidates" part and remove
            # "-candidates" part.
            version, = [
                x.split('-candidates')[0]
                for x in urlparse.urlparse(info_url).path.split('/')
                if x.endswith('-candidates')
            ]
            kvpairs['version_build'] = version_build

            yield (platform, version, kvpairs, bad_lines)


@with_postgres_transactions()
@as_backfill_cron_app
class FTPScraperCronApp(BaseCronApp, ScrapersMixin):
    app_name = 'ftpscraper'
    app_description = 'FTP Scraper'
    app_version = '0.1'

    required_config = Namespace()
    required_config.add_option(
        'products',
        default='firefox,mobile,thunderbird,seamonkey,devedition',
        from_string_converter=lambda line: tuple(
            [x.strip() for x in line.split(',') if x.strip()]
        ),
        doc='a comma-delimited list of URIs for each product')

    required_config.add_option(
        'base_url',
        default='https://archive.mozilla.org/pub/',
        doc='The base url to use for fetching builds')

    required_config.add_option(
        'dry_run',
        default=False,
        doc='Print instead of storing builds')

    required_config.add_option(
        'retries',
        default=5,
        doc='Number of times the requests sessions should retry')

    required_config.add_option(
        'read_timeout',
        default=10,  # seconds
        doc='Number of seconds wait for a full read')

    required_config.add_option(
        'connect_timeout',
        default=3.5,  # seconds, ideally something slightly larger than 3
        doc='Number of seconds wait for a connection')

    required_config.add_option(
        'json_files_to_ignore',
        default='*.mozinfo.json, *test_packages.json',
        from_string_converter=str_to_list
    )

    required_config.add_option(
        'cachedir',
        default='',
        doc=(
            'Directory to cache .json files in. Empty string if you want to '
            'disable caching'
        )
    )

    def __init__(self, *args, **kwargs):
        super(FTPScraperCronApp, self).__init__(*args, **kwargs)
        self.session = requests.Session()
        if urlparse.urlparse(self.config.base_url).scheme == 'https':
            mount = 'https://'
        else:
            mount = 'http://'
        self.session.mount(
            mount,
            HTTPAdapter(max_retries=self.config.retries)
        )

        self.cache_hits = 0
        self.cache_misses = 0

    def url_to_filename(self, url):
        fn = re.sub('\W', '_', url)
        fn = re.sub('__', '_', fn)
        return fn

    @memoize_download
    def download(self, url):
        is_caching = False
        fn = None

        if url.endswith('.json') and self.config.cachedir:
            is_caching = True
            fn = os.path.join(self.config.cachedir, self.url_to_filename(url))
            if not os.path.isdir(os.path.dirname(fn)):
                os.makedirs(os.path.dirname(fn))
            if os.path.exists(fn):
                self.cache_hits += 1
                with open(fn, 'r') as fp:
                    return fp.read()
            self.cache_misses += 1

        response = self.session.get(
            url,
            timeout=(self.config.connect_timeout, self.config.read_timeout)
        )
        if response.status_code == 404:
            self.config.logger.warning(
                '404 when downloading %s', url
            )
            # Legacy. Return None on any 404 error.
            return
        assert response.status_code == 200, response.status_code
        data = response.content

        if is_caching:
            with open(fn, 'w') as fp:
                fp.write(data)

        return data

    def skip_json_file(self, json_url):
        basename = os.path.basename(json_url)
        for file_pattern in self.config.json_files_to_ignore:
            if fnmatch.fnmatch(basename, file_pattern):
                return True
        return False

    def run(self, date):
        # record_associations
        for product_name in self.config.products:
            self.config.logger.debug(
                'scraping %s releases for date %s',
                product_name,
                date
            )
            self.database_transaction_executor(
                self._scrape_json_releases_and_nightlies,
                product_name,
                date
            )

        if self.config.cachedir:
            total = float(self.cache_hits + self.cache_misses)
            self.config.logger.debug('Cache: hits: %d (%2.2f%%) misses: %d (%2.2f%%)' % (
                self.cache_hits,
                self.cache_hits / total * 100,
                self.cache_misses,
                self.cache_misses / total * 100,
            ))

    def _scrape_json_releases_and_nightlies(
        self,
        connection,
        product_name,
        date
    ):
        self.scrape_json_releases(connection, product_name)
        self.scrape_json_nightlies(connection, product_name, date)

    def _insert_build(self, cursor, *args, **kwargs):
        self.config.logger.debug('adding %s', args)
        if self.config.dry_run:
            print('INSERT BUILD')
            print(args)
            print(kwargs)
        else:
            buildutil.insert_build(cursor, *args, **kwargs)

    def _is_final_beta(self, version):
        # If this is a XX.0 version in the release channel,
        # return True otherwise, False
        # Make a special exception for the out-of-cycle 38.0.5
        return version.endswith('.0') or version == '38.0.5'

    def scrape_json_releases(self, connection, product_name):
        prod_url = urlparse.urljoin(self.config.base_url, product_name + '/')
        logger = self.config.logger
        cursor = connection.cursor()

        for directory in ('nightly', 'candidates'):
            try:
                url, = self.get_links(prod_url, starts_with=directory)
            except (IndexError, ValueError):
                logger.debug('Dir %s not found for %s',
                             directory, product_name)
                continue

            releases = self.get_links(url, ends_with='-candidates/')
            for release in releases:
                dirname = release.replace(url, '')
                if dirname.endswith('/'):
                    dirname = dirname[:-1]
                for info in self.get_json_release(release, dirname):
                    platform, version, kvpairs = info
                    build_type = 'release'
                    beta_number = None
                    repository = kvpairs['repository']
                    if 'b' in version:
                        build_type = 'beta'
                        version, beta_number = version.split('b')

                    if kvpairs.get('buildID'):
                        build_id = kvpairs['buildID']
                        version_build = kvpairs['version_build']
                        self._insert_build(
                            cursor,
                            product_name,
                            version,
                            platform,
                            build_id,
                            build_type,
                            beta_number,
                            repository,
                            version_build,
                            ignore_duplicates=True
                        )

                    if (
                        self._is_final_beta(version) and
                        build_type == 'release' and
                        version > '26.0' and
                        kvpairs.get('buildID')
                    ):
                        logger.debug('adding final beta version %s', version)
                        repository = 'mozilla-beta'
                        build_id = kvpairs['buildID']
                        build_type = 'beta'
                        version_build = kvpairs['version_build']
                        # just force this to 99 until
                        # we deal with version_build properly
                        beta_number = 99
                        self._insert_build(
                            cursor,
                            product_name,
                            version,
                            platform,
                            build_id,
                            build_type,
                            beta_number,
                            repository,
                            version_build,
                            ignore_duplicates=True
                        )

    def scrape_json_nightlies(self, connection, product_name, date):
        directories = (
            product_name,
            'nightly',
            date.strftime('%Y'),
            date.strftime('%m'),
        )
        nightly_url = self.config.base_url
        for part in directories:
            nightly_url = urlparse.urljoin(
                nightly_url, part + '/'
            )
        cursor = connection.cursor()
        dir_prefix = date.strftime('%Y-%m-%d')
        nightlies = self.get_links(nightly_url, starts_with=dir_prefix)
        for nightly in nightlies:
            dirname = nightly.replace(nightly_url, '')
            if dirname.endswith('/'):
                dirname = dirname[:-1]
            for info in self.get_json_nightly(nightly, dirname):
                platform, repository, version, kvpairs = info

                build_type = 'nightly'
                if version.endswith('a2'):
                    build_type = 'aurora'

                if kvpairs.get('buildID'):
                    build_id = kvpairs['buildID']
                    self._insert_build(
                        cursor,
                        product_name,
                        version,
                        platform,
                        build_id,
                        build_type,
                        kvpairs.get('beta_number', None),
                        repository,
                        ignore_duplicates=True
                    )


class FTPScraperCronAppDryRunner(App):  # pragma: no cover
    """This is a utility class that makes it easy to run the scraping
    and ALWAYS do so in a "dry run" fashion such that stuff is never
    stored in the database but instead found releases are just printed
    out stdout.

    To run it, simply execute this file:

        $ python socorro/cron/jobs/ftpscraper.py

    If you want to override what date to run it for (by default it's
    "now") you simply use this format:

        $ python socorro/cron/jobs/ftpscraper.py --date=2015-10-23

    By default it runs for every, default configured, product
    (see the configuration set up in the FTPScraperCronApp above). You
    can override that like this:

        $ python socorro/cron/jobs/ftpscraper.py --product=mobile,thunderbird

    """

    required_config = Namespace()
    required_config.add_option(
        'date',
        default=datetime.datetime.utcnow().date(),
        doc='Date to run for',
        from_string_converter=string_to_datetime
    )
    required_config.add_option(
        'crontabber_job_class',
        default='socorro.cron.jobs.ftpscraper.FTPScraperCronApp',
        doc='bla',
        from_string_converter=class_converter,
    )

    @staticmethod
    def get_application_defaults():
        return {
            'database.database_class': mock.MagicMock()
        }

    def __init__(self, config):
        self.config = config
        self.config.dry_run = True
        self.ftpscraper = config.crontabber_job_class(config, {})

    def main(self):
        assert self.config.dry_run
        self.ftpscraper.run(self.config.date)


if __name__ == '__main__':  # pragma: no cover
    sys.exit(FTPScraperCronAppDryRunner.run())
