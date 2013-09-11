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


def getLinks(url, startswith=None, endswith=None):

    html = ''
    results = []
    _attempts = 0
    while True:
        if _attempts > 3:
            raise RetriedError(_attempts, url)
        try:
            _attempts += 1
            page = urllib2.urlopen(url)
        except urllib2.HTTPError, err:
            # wait half a minute
            time.sleep(30)
            if err.code == 404:
                return results
            elif err.code < 500:
                raise
        except urllib2.URLError, err:
            # wait half a minute
            time.sleep(30)
            pass
        else:
            html = lxml.html.document_fromstring(page.read())
            page.close()
            break

    for element, attribute, link, pos in html.iterlinks():
        if startswith:
            if link.startswith(startswith):
                results.append(link)
        elif endswith:
            if link.endswith(endswith):
                results.append(link)
    return results


def parseInfoFile(url, nightly=False):
    infotxt = urllib2.urlopen(url)
    content = infotxt.read()
    contents = content.splitlines()
    infotxt.close()
    results = {}
    bad_lines = []
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
      Example: {"buildid": "20130125070201", "update_channel": "nightly", "version": "18.0"}
      TODO handle exception if file does not exist
    """
    infotxt = urllib2.urlopen(url)
    results = json.load(infotxt)
    infotxt.close()

    # bug 869564: Return None if update_channel is 'default'
    if results['update_channel'] == 'default':
        logger.warning("Found default update_channel for buildid: %s. Skipping.", results['buildid'])
        return None

    # Default 'null' channels to nightly
    results['build_type'] = results['update_channel'] or 'nightly'

    # Default beta_number to 1 for beta releases
    if results['update_channel'] == 'beta':
        results['beta_number'] = results.get('beta_number', 1)

    return results


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
        build_number = latest_build.strip('/')

        yield (platform, version, build_number, kvpairs, bad_lines)


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
        from_string_converter=\
          lambda x: tuple([x.strip() for x in x.split(',') if x.strip()]),
        doc='a comma-delimited list of URIs for each product')

    required_config.add_option(
        'base_url',
        default='http://ftp.mozilla.org/pub/mozilla.org',
        doc='The base url to use for fetching builds')

    def run(self, connection, date):
        # record_associations
        logger = self.config.logger

        for product_name in self.config.products:
            logger.debug('scraping %s releases for date %s',
                product_name, date)
            if product_name == 'b2g':
                self.scrapeB2G(connection, product_name, date)
            else:
                self.scrapeReleases(connection, product_name)
                self.scrapeNightlies(connection, product_name, date)


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
                    platform, version, build_number, kvpairs, bad_lines = info
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
                        buildutil.insert_build(
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
                    buildutil.insert_build(
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
        b2g_manifests = urljoin(self.config.base_url, product_name,
                            'manifests', 'nightly')

        dir_prefix = date.strftime('%Y-%m-%d')
        version_dirs = getLinks(b2g_manifests, startswith='1.')
        for version_dir in version_dirs:
            prod_url = urljoin(b2g_manifests, version_dir,
                               date.strftime('%Y'), date.strftime('%m'))
            nightlies = getLinks(prod_url, startswith=dir_prefix)

            for nightly in nightlies:
                for info in getB2G(nightly, prod_url, backfill_date=None, logger=self.config.logger):
                    (platform, repository, version, kvpairs) = info
                    build_id = kvpairs['buildid']
                    build_type = kvpairs['build_type']
                    buildutil.insert_build(
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
