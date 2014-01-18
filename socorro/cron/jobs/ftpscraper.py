import re
import urllib2
import lxml.html
import json
import time
from configman import Namespace
from socorro.cron.base import PostgresBackfillCronApp
from socorro.lib import buildutil
import os

"""
 Socket timeout to prevent FTP from hanging indefinitely
 Picked a 2 minute timeout as a generous allowance,
 given the entire script takes about that much time to run.
"""
import socket
socket.setdefaulttimeout(60)

#==============================================================================


class RetriedError(IOError):

    def __init__(self, attempts, url):
        self.attempts = attempts
        self.url = url

    def __str__(self):
        return (
            '<%s: %s attempts at downloading %s>' %
            (self.__class__.__name__, self.attempts, self.url)
        )


def urljoin(*parts):
    url = parts[0]
    for part in parts[1:]:
        if not url.endswith('/'):
            url += '/'
        if part.startswith('/'):
            part = part[1:]
        url += part
    return url


def patient_urlopen(url, max_attempts=4, sleep_time=20):
    attempts = 0
    while True:
        if attempts >= max_attempts:
            raise RetriedError(attempts, url)
        try:
            attempts += 1
            page = urllib2.urlopen(url)
        except urllib2.HTTPError, err:
            if err.code == 404:
                return
            if err.code < 500:
                raise
            time.sleep(sleep_time)
        except urllib2.URLError, err:
            time.sleep(sleep_time)
        else:
            content = page.read()
            page.close()
            return content


def getLinks(url, startswith=None, endswith=None):

    html = ''
    results = []
    content = patient_urlopen(url, sleep_time=30)
    if not content:
        return []
    html = lxml.html.document_fromstring(content)

    for element, attribute, link, pos in html.iterlinks():
        if startswith:
            if link.startswith(startswith):
                results.append(link)
        elif endswith:
            if link.endswith(endswith):
                results.append(link)
    return results


def parseBuildJsonFile(url, nightly=False):
    content = patient_urlopen(url)
    if not content:
        return
    results = json.loads(content)

    return results


def parseInfoFile(url, nightly=False):
    content = patient_urlopen(url)
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


def parseB2GFile(url, nightly=False, logger=None):
    """
      Parse the B2G manifest JSON file
      Example: {"buildid": "20130125070201", "update_channel":
                "nightly", "version": "18.0"}
      TODO handle exception if file does not exist
    """
    content = patient_urlopen(url)
    if not content:
        return
    results = json.loads(content)

    # bug 869564: Return None if update_channel is 'default'
    if results['update_channel'] == 'default' and logger:
        logger.warning(
            "Found default update_channel for buildid: %s. Skipping.",
            results['buildid']
        )
        return

    # Default 'null' channels to nightly
    results['build_type'] = results['update_channel'] or 'nightly'

    # Default beta_number to 1 for beta releases
    if results['update_channel'] == 'beta':
        results['beta_number'] = results.get('beta_number', 1)

    return results


def getJsonRelease(dirname, url):
    candidate_url = urljoin(url, dirname)
    version = dirname.split('-candidates')[0]

    builds = getLinks(candidate_url, startswith='build')
    if not builds:
        return

    latest_build = builds.pop()
    build_url = urljoin(candidate_url, latest_build)

    for platform in ['linux', 'mac', 'win', 'debug']:
        platform_urls = getLinks(build_url, startswith=platform)
        for p in platform_urls:
            platform_url = urljoin(build_url, p)
            platform_local_url = urljoin(platform_url, 'en-US/')
            json_files = getLinks(platform_local_url, endswith='.json')

            for f in json_files:
                json_url = urljoin(build_url, f)
                kvpairs = parseBuildJsonFile(json_url)

                kvpairs['repository'] = kvpairs['moz_source_repo'].split('/', -1)[-1]
                kvpairs['build_type'] = kvpairs['moz_update_channel']
                kvpairs['buildID'] = kvpairs['buildid']

                yield (platform, version, kvpairs)


def getRelease(dirname, url):
    candidate_url = urljoin(url, dirname)
    builds = getLinks(candidate_url, startswith='build')
    if not builds:
        #logger.info('No build dirs in %s' % candidate_url)
        return

    latest_build = builds.pop()
    build_url = urljoin(candidate_url, latest_build)
    info_files = getLinks(build_url, endswith='_info.txt')

    for f in info_files:
        info_url = urljoin(build_url, f)
        kvpairs, bad_lines = parseInfoFile(info_url)

        platform = f.split('_info.txt')[0]

        version = dirname.split('-candidates')[0]

        yield (platform, version, kvpairs, bad_lines)


def getNightly(dirname, url):
    nightly_url = urljoin(url, dirname)

    info_files = getLinks(nightly_url, endswith='.txt')
    for f in info_files:
        if 'en-US' in f:
            pv, platform = re.sub('\.txt$', '', f).split('.en-US.')
        elif 'multi' in f:
            pv, platform = re.sub('\.txt$', '', f).split('.multi.')
        else:
            ##return
            continue

        version = pv.split('-')[-1]
        repository = []

        for field in dirname.split('-'):
            if not field.isdigit():
                repository.append(field)
        repository = '-'.join(repository).strip('/')

        info_url = urljoin(nightly_url, f)
        kvpairs, bad_lines = parseInfoFile(info_url, nightly=True)

        yield (platform, repository, version, kvpairs, bad_lines)


def getB2G(dirname, url, backfill_date=None, logger=None):
    """
     Last mile of B2G scraping, calls parseB2G on .json
     Files look like:  socorro_unagi-stable_2013-01-25-07.json
    """
    url = '%s/%s' % (url, dirname)
    info_files = getLinks(url, endswith='.json')
    platform = None
    version = None
    repository = 'b2g-release'
    for f in info_files:
        # Pull platform out of the filename
        jsonfilename = os.path.splitext(f)[0].split('_')

        # Skip if this file isn't for socorro!
        if jsonfilename[0] != 'socorro':
            continue
        platform = jsonfilename[1]

        info_url = '%s/%s' % (url, f)
        kvpairs = parseB2GFile(info_url, nightly=True, logger=logger)

        # parseB2GFile() returns None when a file is
        #    unable to be parsed or we ignore the file
        if kvpairs is None:
            continue
        version = kvpairs['version']

        yield (platform, repository, version, kvpairs)


#==============================================================================
class FTPScraperCronApp(PostgresBackfillCronApp):
    app_name = 'ftpscraper'
    app_description = 'FTP Scraper'
    app_version = '0.1'

    required_config = Namespace()
    required_config.add_option(
        'products',
        default='firefox,mobile,thunderbird,seamonkey,b2g',
        from_string_converter=lambda line: tuple(
            [x.strip() for x in line.split(',') if x.strip()]
        ),
        doc='a comma-delimited list of URIs for each product')

    required_config.add_option(
        'base_url',
        default='http://ftp.mozilla.org/pub/mozilla.org',
        doc='The base url to use for fetching builds')

    required_config.add_option(
        'dry_run',
        default=False,
        doc='Print instead of storing builds')

    def run(self, connection, date):
        # record_associations
        logger = self.config.logger

        for product_name in self.config.products:
            logger.debug('scraping %s releases for date %s',
                         product_name, date)
            if product_name == 'b2g':
                self.scrapeB2G(connection, product_name, date)
            elif product_name == 'firefox':
                self.scrapeJsonReleases(connection, product_name)
            else:
                self.scrapeReleases(connection, product_name)
                self.scrapeNightlies(connection, product_name, date)

    def _insert_build(self, cursor, *args, **kwargs):
        if self.config.dry_run:
            print "INSERT BUILD"
            for arg in args:
                print "\t", repr(arg)
            for key in kwargs:
                print "\t%s=" % key, repr(kwargs[key])
        else:
            buildutil.insert_build(cursor, *args, **kwargs)

    def _is_final_beta(self, version):
        # if this is a XX.0 version in the release channel,
        # return True otherwise, False
        version_parts = version.split('.')
        if version_parts[1] == '0' and len(version_parts) == 2:
            return True
        else:
            return False


    def scrapeJsonReleases(self, connection, product_name):
        prod_url = urljoin(self.config.base_url, product_name, '')
        logger = self.config.logger
        cursor = connection.cursor()

        for directory in ('nightly', 'candidates'):
            if not getLinks(prod_url, startswith=directory):
                logger.debug('Dir %s not found for %s',
                             directory, product_name)
                continue

            url = urljoin(self.config.base_url, product_name, directory, '')
            releases = getLinks(url, endswith='-candidates/')
            for release in releases:
                for info in getJsonRelease(release, url):
                    platform, version, kvpairs = info
                    build_type = 'release'
                    beta_number = None
                    repository = kvpairs['repository']
                    if 'b' in version:
                        build_type = 'beta'
                        version, beta_number = version.split('b')

                    if kvpairs.get('buildID'):
                        build_id = kvpairs['buildID']
                        self._insert_build(
                            cursor,
                            product_name,
                            version,
                            platform,
                            build_id,
                            build_type,
                            beta_number,
                            repository,
                            ignore_duplicates=True
                        )

                    if self._is_final_beta(version):
                        repository = 'mozilla-beta'
                        build_id = kvpairs['buildID']
                        self._insert_build(
                            cursor,
                            product_name,
                            version,
                            platform,
                            build_id,
                            build_type,
                            beta_number,
                            repository,
                            ignore_duplicates=True
                        )

    def scrapeReleases(self, connection, product_name):
        prod_url = urljoin(self.config.base_url, product_name, '')
        # releases are sometimes in nightly, sometimes in candidates dir.
        # look in both.
        logger = self.config.logger
        cursor = connection.cursor()
        for directory in ('nightly', 'candidates'):
            if not getLinks(prod_url, startswith=directory):
                logger.debug('Dir %s not found for %s',
                             directory, product_name)
                continue

            url = urljoin(self.config.base_url, product_name, directory, '')
            releases = getLinks(url, endswith='-candidates/')
            for release in releases:
                for info in getRelease(release, url):
                    platform, version, kvpairs, bad_lines = info
                    build_type = 'Release'
                    beta_number = None
                    repository = 'mozilla-release'
                    if 'b' in version:
                        build_type = 'Beta'
                        version, beta_number = version.split('b')
                        repository = 'mozilla-beta'
                    for bad_line in bad_lines:
                        self.config.logger.warning(
                            "Bad line for %s on %s (%r)",
                            release, url, bad_line
                        )
                    if kvpairs.get('buildID'):
                        build_id = kvpairs['buildID']
                        self._insert_build(
                            cursor,
                            product_name,
                            version,
                            platform,
                            build_id,
                            build_type,
                            beta_number,
                            repository,
                            ignore_duplicates=True
                        )

                    if self._is_final_beta(version):
                        repository = 'mozilla-beta'
                        build_id = kvpairs['buildID']
                        self._insert_build(
                            cursor,
                            product_name,
                            version,
                            platform,
                            build_id,
                            build_type,
                            beta_number,
                            repository,
                            ignore_duplicates=True
                        )

    def scrapeNightlies(self, connection, product_name, date):
        nightly_url = urljoin(self.config.base_url, product_name, 'nightly',
                              date.strftime('%Y'),
                              date.strftime('%m'),
                              '')
        cursor = connection.cursor()
        dir_prefix = date.strftime('%Y-%m-%d')
        nightlies = getLinks(nightly_url, startswith=dir_prefix)
        for nightly in nightlies:
            for info in getNightly(nightly, nightly_url):
                platform, repository, version, kvpairs, bad_lines = info
                for bad_line in bad_lines:
                    self.config.logger.warning(
                        "Bad line for %s (%r)",
                        nightly, bad_line
                    )
                build_type = 'Nightly'
                if version.endswith('a2'):
                    build_type = 'Aurora'
                if kvpairs.get('buildID'):
                    build_id = kvpairs['buildID']
                    self._insert_build(
                        cursor,
                        product_name,
                        version,
                        platform,
                        build_id,
                        build_type,
                        None,
                        repository,
                        ignore_duplicates=True
                    )

    def scrapeB2G(self, connection, product_name, date):

        if not product_name == 'b2g':
            return
        cursor = connection.cursor()
        b2g_manifests = urljoin(
            self.config.base_url,
            product_name,
            'manifests',
            'nightly'
        )

        dir_prefix = date.strftime('%Y-%m-%d')
        version_dirs = getLinks(b2g_manifests, startswith='1.')
        for version_dir in version_dirs:
            prod_url = urljoin(
                b2g_manifests,
                version_dir,
                date.strftime('%Y'),
                date.strftime('%m')
            )
            nightlies = getLinks(prod_url, startswith=dir_prefix)

            for nightly in nightlies:
                b2gs = getB2G(
                    nightly,
                    prod_url,
                    backfill_date=None,
                    logger=self.config.logger
                )
                for info in b2gs:
                    (platform, repository, version, kvpairs) = info
                    build_id = kvpairs['buildid']
                    build_type = kvpairs['build_type']
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


import datetime
import sys
from socorro.app.generic_app import main


class _MockConnection(object):  # pragma: no cover
    """When running the FTPScraperCronAppRunner app, it never actually
    needs a database connection because instead of doing an insert
    it just prints. However, it primes the connection by getting a cursor
    out first (otherwise it'd have to do it every time in a loo[).
    """

    def cursor(self):
        pass


class FTPScraperCronAppRunner(FTPScraperCronApp):  # pragma: no cover

    required_config = Namespace()
    required_config.add_option(
        'date',
        default=datetime.datetime.utcnow(),
        doc='Date to run for',
        from_string_converter='socorro.lib.datetimeutil.string_to_datetime'
    )

    def __init__(self, config):
        self.config = config
        self.config.dry_run = True

    def main(self):
        assert self.config.dry_run
        self.run(_MockConnection(), self.config.date)


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(FTPScraperCronAppRunner))
