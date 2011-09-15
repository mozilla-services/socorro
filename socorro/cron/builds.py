#! /usr/bin/env python
"""
builds.py is used to get the primary nightly builds from ftp.mozilla.org, record
the build information and provide that information through the Crash Reporter website.

This script is expected to be run once per day, and will be called from scripts/startBuilds.py.
"""

import logging
import os
import urllib2
from sgmllib import SGMLParser

logger = logging.getLogger("builds")

import socorro.lib.psycopghelper as psy
import socorro.lib.util as util


def nightlyBuildExists(databaseCursor, product, version, platform, buildid):
  """ Determine whether or not a particular build exists already in the database """
  sql = """
    SELECT *
    FROM builds
    WHERE product = %s
    AND version = %s
    AND platform = %s
    AND buildid = %s
  """

  values = (product, version, platform, buildid)
  exists = buildExists(databaseCursor, sql, values)
  if not exists:
    logger.info("Did not find build entries in builds table for %s %s %s %s" % (product, version, platform, buildid))

  return exists

def releaseBuildExists(databaseCursor, product, version, buildid, buildType, platform, betanum):
  """ Determine whether or not a particular release build exists already in the database """
  sql = """
    SELECT *
    FROM releases_raw
    WHERE product_name = %s
    AND version = %s
    AND platform = %s
    AND build_id = %s
    AND build_type = %s
  """

  if betanum is not None:
    sql += """ AND beta_number = %s """
  else:
    sql += """ AND beta_number IS %s """

  values = (product, version, platform, buildid, buildType, betanum)
  exists = buildExists(databaseCursor, sql, values)
  if not exists:
    logger.info("Did not find build entries in releases_raw table for %s %s %s %s %s %s" % (product, version, buildid, buildType, platform, betanum))

  return exists

def buildExists(databaseCursor, sql, values):
  databaseCursor.execute(sql, values)
  result = databaseCursor.fetchone()

  return result is not None

def fetchBuild(build_url, urllib2=urllib2):
  """ Grab a particular build from the Mozilla FTP site. """
  response = urllib2.urlopen(build_url)
  if response.code == 200:
    data = response.read()
    response.close()
    try:
      return data.strip().split()
    except Exception:
      util.reportExceptionAndAbort(logger)
      return None
  else:
    util.reportExceptionAndAbort(logger)
    return None


def insertBuild(databaseCursor, product, version, platform, buildid, platform_changeset, app_changeset_1, app_changeset_2, filename):
  """ Insert a particular build into the database """
  build = nightlyBuildExists(databaseCursor, product, version, platform, buildid)
  if not build:
    sql = """
      INSERT INTO builds
      (product, version, platform, buildid, platform_changeset, app_changeset_1, app_changeset_2, filename)
      VALUES
      (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    try:
      values = (product, version, platform, buildid, platform_changeset, app_changeset_1, app_changeset_2, filename)
      databaseCursor.execute(sql, values)
      databaseCursor.connection.commit()
      logger.info("Inserted the following build: %s %s %s %s %s %s %s %s" % (product, version, platform, buildid, platform_changeset, app_changeset_1, app_changeset_2, filename))
    except Exception:
      databaseCursor.connection.rollback()
      util.reportExceptionAndAbort(logger)

def insertReleaseBuild(databaseCursor, product, version, buildid, buildType, betanum, platform):
  """ Insert a particular build into the database """
  build = releaseBuildExists(databaseCursor, product, version, buildid, buildType, platform, betanum)
  if not build:
    sql = """
      INSERT INTO releases_raw
      (product_name, version, platform, build_id, build_type, beta_number)
      VALUES
      (%s, %s, %s, %s, %s, %s)
    """

    try:
      values = (product, version, platform, buildid, buildType, betanum)
      databaseCursor.execute(sql, values)
      databaseCursor.connection.commit()
      logger.info("Inserted the following build: %s %s %s %s %s %s" % (product, version, platform, buildid, buildType, betanum))
    except Exception:
      databaseCursor.connection.rollback()
      util.reportExceptionAndAbort(logger)

class buildParser(SGMLParser):
  """ Class for parsing href links; should replace with Beautiful Soup - SGML has been deprecated """
  def reset(self):
    SGMLParser.reset(self)
    self.builds = []

  def start_a(self, attributes):
    for (attr, filename) in attributes:
      if attr == 'href':
        if filename.endswith(".txt"):
          platform = filename.split('.')[-2]
          if platform in self.platforms:
            chunks = filename.split("-")
            product = chunks[0]
            version = chunks[1].split(".en")[0]
            self.builds.append(({'platform':platform, 'product':product, 'version':version, 'filename':filename}))

class releaseBuildParser(SGMLParser):
  """ Class for parsing href links; should replace with Beautiful Soup - SGML has been deprecated """
  def reset(self):
    SGMLParser.reset(self)
    self.builds = []

  def start_a(self, attributes):
    for (attr, filename) in attributes:
      if attr == 'href':
        if filename.endswith(".txt"):
          platform = filename.split('_info.txt')[0]
          if platform in self.platforms:
            self.builds.append(({'platform':platform, 'filename':filename}))

class buildParser(SGMLParser):
  """ Class for parsing href links; should replace with Beautiful Soup - SGML has been deprecated """
  def reset(self):
    SGMLParser.reset(self)
    self.builds = []

  def start_a(self, attributes):
    for (attr, filename) in attributes:
      if attr == 'href':
        if filename.endswith(".txt"):
          platform = filename.split('.')[-2]
          if platform in self.platforms:
            chunks = filename.split("-")
            product = chunks[0]
            version = chunks[1].split(".en")[0]
            self.builds.append(({'platform':platform, 'product':product, 'version':version, 'filename':filename}))


def fetchTextFiles(config, product_uri, platforms, parser, urllib2=urllib2):
  """ Parse the FTP site to find the build information for the latest nightly builds """
  url = "%s%s" % (config.base_url, product_uri)
  try:
    response = urllib2.urlopen(url)
    if response.code == 200:
      parser.platforms = platforms
      parser.feed(response.read())
      response.close()
      parser.close()
      return {'url':url, 'builds':parser.builds}
    else:
      logger.info("Nothing available at %s" % (url))
      return None
  except Exception:
    util.reportExceptionAndContinue(logger)
    return None

class candidateParser(SGMLParser):
  """ Class for parsing href links; should replace with Beautiful Soup - SGML has been deprecated """
  def reset(self):
    SGMLParser.reset(self)
    self.candidates = []

  def start_a(self, attributes):
    for (attr, dirname) in attributes:
      if attr == 'href':
        if dirname.endswith('-candidates/'):
          self.candidates.append(({'dirname':dirname}))

def fetchReleaseCandidates(config, product_uri, urllib2=urllib2):
  """ Parse the FTP site to find the build information for the latest release candidates """
  url = "%s%s" % (config.base_url, product_uri)
  try:
    response = urllib2.urlopen(url)
    if response.code == 200:
      parser = candidateParser()
      parser.platforms = config.release_platforms
      parser.feed(response.read())
      response.close()
      parser.close()
      return {'url':url, 'candidates':parser.candidates}
    else:
      logger.info("Nothing available at %s" % (url))
      return None
  except Exception:
    logger.info('Exception downloading from url %s' % (url))
    util.reportExceptionAndContinue(logger)
    return None

def fetchAndRecordNightlyBuilds(config, databaseCursor, urllib2=urllib2):
  for product_uri in config.product_uris:
    builds = fetchTextFiles(config, product_uri, config.platforms, buildParser())
    try:
      if 'builds' in builds:
        for build in builds['builds']:
          build_url = "%s%s" % (builds['url'], build['filename'])
          build_file = fetchBuild(build_url, urllib2)
          if build_file:
            buildid = build_file[0]
            platform_changeset = ''
            app_changeset_1 = ''
            app_changeset_2 = ''

            try:
              if len(build_file) >= 2:
                platform_changeset = os.path.basename(build_file[1])
            except Exception:
              util.reportExceptionAndContinue(logger, 30)
            try:
              if len(build_file) >= 3:
                app_changeset_1 = os.path.basename(build_file[2])
            except Exception:
              util.reportExceptionAndContinue(logger, 30)
            try:
              if len(build_file) >= 4:
                app_changeset_2 = os.path.basename(build_file[3])
            except Exception:
              util.reportExceptionAndContinue(logger, 30)

            insertBuild(databaseCursor, build['product'], build['version'], build['platform'], buildid, platform_changeset, app_changeset_1, app_changeset_2, build['filename'])
    except Exception:
      util.reportExceptionAndContinue(logger, 30)

class candidateBuildParser(SGMLParser):
  """ Class for parsing href links; should replace with Beautiful Soup - SGML has been deprecated """
  def reset(self):
    SGMLParser.reset(self)
    self.builds = []

  def start_a(self, attributes):
    for (attr, dirname) in attributes:
      if attr == 'href':
        if dirname.startswith('build'):
          self.builds.append(dirname)

def findLatestBuild(config, candidateUrl, urllib2=urllib2):
  """ Parse the FTP site to find the latest build dir for release candidates """
  url = "%s%s" % (config.base_url, candidateUrl)
  try:
    response = urllib2.urlopen(url)
    if response.code == 200:
      parser = candidateBuildParser()
      parser.platforms = config.release_platforms
      parser.feed(response.read())
      response.close()
      parser.close()
      return {'url':url, 'builds':parser.builds}
    else:
      logger.info("Nothing available at %s" % (url))
      return None
  except Exception:
    util.reportExceptionAndContinue(logger)
    return None

def recordNightlyBuilds(config):
  databaseConnectionPool = psy.DatabaseConnectionPool(config.databaseHost, config.databaseName, config.databaseUserName, config.databasePassword, logger)
  try:
    databaseConnection, databaseCursor = databaseConnectionPool.connectionCursorPair()
    fetchAndRecordNightlyBuilds(config, databaseCursor)
  finally:
    databaseConnectionPool.cleanup()

def fetchAndRecordReleaseBuilds(config, databaseCursor, urllib2=urllib2):
  for product_uri in config.release_product_uris:
    candidates = fetchReleaseCandidates(config, product_uri, urllib2)
    for candidate in candidates['candidates']:
      version = candidate['dirname'].split('-candidates')[0]
      betanum = None
      buildType = 'Release'
      if 'b' in version:
        buildType = 'Beta'
        (version,betanum) = version.split('b')
      candidateUrl = '/'.join([product_uri, candidate['dirname']])
      builds = findLatestBuild(config, candidateUrl)
      if builds is None:
        continue
      builds['builds'].sort()
      buildUrl = '/'.join([candidateUrl, builds['builds'].pop()])
      builds = fetchTextFiles(config, buildUrl, config.release_platforms, releaseBuildParser())
      product = product_uri.split('/')[0]
      try:
        if builds and 'builds' in builds:
          for build in builds['builds']:
            platform = build['platform']
            build_url = "%s/%s" % (builds['url'], build['filename'])
            build_file = fetchBuild(build_url, urllib2)
            if build_file:
              buildid = build_file[0].split('buildID=')[1]
              insertReleaseBuild(databaseCursor, product, version, buildid, buildType, betanum, platform)
      except Exception:
        util.reportExceptionAndContinue(logger, 30)

def recordReleaseBuilds(config):
  databaseConnectionPool = psy.DatabaseConnectionPool(config.databaseHost, config.databaseName, config.databaseUserName, config.databasePassword, logger)
  try:
    databaseConnection, databaseCursor = databaseConnectionPool.connectionCursorPair()
    fetchAndRecordReleaseBuilds(config, databaseCursor)
  finally:
    databaseConnectionPool.cleanup()
