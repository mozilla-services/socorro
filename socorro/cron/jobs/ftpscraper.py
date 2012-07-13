import re
import urllib2
import lxml.html
from configman import Namespace
from socorro.cron.crontabber import PostgresBackfillCronApp
from socorro.lib import buildutil


#==============================================================================

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
    page = urllib2.urlopen(url)
    html = lxml.html.document_fromstring(page.read())
    page.close()

    results = []
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
    if nightly:
        results = {'buildID': contents[0], 'rev': contents[1]}
        if len(contents) > 2:
            results['altrev'] = contents[2]
    elif contents:
        results = dict(line.split('=') for line in contents)

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
        kvpairs = parseInfoFile(info_url)

        platform = f.split('_info.txt')[0]

        version = dirname.split('-candidates')[0]
        build_number = latest_build.strip('/')

        yield (platform, version, build_number, kvpairs)


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
        kvpairs = parseInfoFile(info_url, nightly=True)

        yield (platform, repository, version, kvpairs)


#==============================================================================
class FTPScraperCronApp(PostgresBackfillCronApp):
    app_name = 'ftpscraper'
    app_description = 'FTP Scraper'
    app_version = '0.1'

    required_config = Namespace()
    required_config.add_option(
        'products',
        default='firefox,mobile,thunderbird,seamonkey',
        from_string_converter=\
          lambda x: tuple([x.strip() for x in x.split(',') if x.strip()]),
        doc='a comma-delimited list of URIs for each product')

    required_config.add_option(
        'base_url',
        default='http://ftp.mozilla.org/pub/mozilla.org',
        doc='The base url to use for fetching builds')

    def run(self, connection, date):
        # record_associations
        logger = self.config.logging.logger

        for product_name in self.config.products:
            self.scrapeReleases(connection, product_name)
            logger.debug('backfilling for date %s', date)
            self.scrapeNightlies(connection, product_name, date)

    def scrapeReleases(self, connection, product_name):
        prod_url = urljoin(self.config.base_url, product_name, '')
        # releases are sometimes in nightly, sometimes in candidates dir.
        # look in both.
        logger = self.config.logging.logger
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
                    platform, version, build_number, kvpairs = info
                    build_type = 'Release'
                    beta_number = None
                    repository = 'mozilla-release'
                    if 'b' in version:
                        build_type = 'Beta'
                        version, beta_number = version.split('b')
                        repository = 'mozilla-beta'
                    build_id = kvpairs['buildID']
                    buildutil.insert_build(cursor,
                                           product_name,
                                           version,
                                           platform,
                                           build_id,
                                           build_type,
                                           beta_number,
                                           repository,
                                           ignore_duplicates=True)

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
                platform, repository, version, kvpairs = info
                build_id = kvpairs['buildID']
                build_type = 'Nightly'
                if version.endswith('a2'):
                    build_type = 'Aurora'
                buildutil.insert_build(cursor,
                                       product_name,
                                       version,
                                       platform,
                                       build_id,
                                       build_type,
                                       None,
                                       repository,
                                       ignore_duplicates=True)
