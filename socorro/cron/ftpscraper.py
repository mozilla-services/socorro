#! /usr/bin/env python
"""
ftpscraper.py pulls build information from ftp.mozilla.org for
nightly and release builds.
"""
import sys
import logging
import urllib2

import socorro.lib.psycopghelper as psy
import socorro.lib.util as util

import lxml.html

logger = logging.getLogger("ftpscraper")


def getLinks(url, startswith=None, endswith=None, urllib=urllib2):
    page = urllib.urlopen(url)
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


def parseInfoFile(url, nightly=False, urllib=urllib2):
    infotxt = urllib.urlopen(url)
    contents = infotxt.read().split()
    infotxt.close()
    results = {}
    if nightly:
        results = {'buildID': contents[0], 'rev': contents[1]}
        if len(contents) > 2:
            results['altrev'] = contents[2]
    else:
        for entry in contents:
            (k, v) = entry.split('=')
            results[k] = v

    return results


def getRelease(dirname, url, urllib=urllib2):
    candidate_url = '%s/%s' % (url, dirname)
    builds = getLinks(candidate_url, startswith='build', urllib=urllib)
    latest_build = builds.pop()
    build_url = '%s/%s' % (candidate_url, latest_build)

    info_files = getLinks(build_url, endswith='_info.txt', urllib=urllib)

    for f in info_files:
        info_url = '%s/%s' % (build_url, f)
        kvpairs = parseInfoFile(info_url)

        platform = f.split('_info.txt')[0]

        version = dirname.split('-candidates')[0]
        build_number = latest_build.strip('/')

        yield (platform, version, build_number, kvpairs)


def getNightly(dirname, url, urllib=urllib2):
    nightly_url = '%s/%s' % (url, dirname)
    info_files = getLinks(nightly_url, endswith='.txt', urllib=urllib)

    for f in info_files:
        if 'en-US' in f:
            (pv, platform) = f.strip('.txt').split('.en-US.')
            (product, version) = pv.split('-')
            repository = dirname.strip('/')

            info_url = '%s/%s' % (nightly_url, f)
            kvpairs = parseInfoFile(info_url, nightly=True)

            yield (platform, repository, version, kvpairs)


def recordBuilds(config):
    databaseConnectionPool = psy.DatabaseConnectionPool(config.databaseHost,
      config.databaseName, config.databaseUserName, config.databasePassword,
      logger)

    try:
        connection, cursor = databaseConnectionPool.connectionCursorPair()
        scrape(config, cursor)
    finally:
        databaseConnectionPool.cleanup()


def buildExists(cursor, product_name, version, platform, build_id, build_type,
                beta_number, repository):
    """ Determine whether or not a particular release build exists already """
    sql = """
        SELECT *
        FROM releases_raw
        WHERE product_name = %s
        AND version = %s
        AND platform = %s
        AND build_id = %s
        AND build_type = %s
    """

    if beta_number is not None:
        sql += """ AND beta_number = %s """
    else:
        sql += """ AND beta_number IS %s """

    sql += """ AND repository = %s """

    params = (product_name, version, platform, build_id, build_type,
              beta_number, repository)
    cursor.execute(sql, params)
    exists = cursor.fetchone()

    return exists != None


def insertBuild(cursor, product_name, version, platform, build_id, build_type,
                beta_number, repository):
    """ Insert a particular build into the database """
    if not buildExists(cursor, product_name, version, platform, build_id,
                       build_type, beta_number, repository):
        sql = """ INSERT INTO releases_raw
                  (product_name, version, platform, build_id, build_type,
                   beta_number, repository)
                  VALUES (%s, %s, %s, %s, %s, %s, %s)"""

        try:
            params = (product_name, version, platform, build_id, build_type,
                      beta_number, repository)
            cursor.execute(sql, params)
            cursor.connection.commit()
            logger.info("Inserted: %s %s %s %s %s %s %s" % params)
        except Exception:
            cursor.connection.rollback()
            util.reportExceptionAndAbort(logger)


def scrape(config, cursor, urllib=urllib2):
    for product_name in config.products:
        for dir in ('nightly', 'candidates'):
            prod_url = '%s/%s/' % (config.base_url, product_name)
            if not getLinks(prod_url, startswith=dir, urllib=urllib):
                logger.debug('Dir %s not found for %s' % (dir, product_name))
                continue

            url = '%s/%s/%s/' % (config.base_url, product_name, dir)

            try:
                releases = getLinks(url, endswith='-candidates/',
                                    urllib=urllib)
                for release in releases:
                    for info in getRelease(release, url):
                        (platform, version, build_number, kvpairs) = info
                        build_type = 'Release'
                        beta_number = None
                        repository = 'mozilla-release'
                        if 'b' in version:
                            build_type = 'Beta'
                            version, beta_number = version.split('b')
                            repository = 'mozilla-beta'
                        build_id = kvpairs['buildID']
                        insertBuild(cursor, product_name, version, platform,
                                    build_id, build_type, beta_number,
                                    repository)

                nightlies = getLinks(url, startswith='latest', urllib=urllib)
                for nightly in nightlies:
                    for info in getNightly(nightly, url):
                        (platform, repository, version, kvpairs) = info
                        build_id = kvpairs['buildID']
                        build_type = 'Nightly'
                        if version.endswith('a2'):
                            build_type = 'Aurora'
                        version = version.split('a')[0]
                        insertBuild(cursor, product_name, version, platform,
                                    build_id, build_type, None, repository)

            except urllib.URLError, e:
                if not hasattr(e, "code"):
                    raise
                resp = e
                print >> sys.stderr, 'HTTP code %s for URL %s' %  \
                  (resp.code, url)
