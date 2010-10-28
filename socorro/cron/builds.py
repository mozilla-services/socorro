#! /usr/bin/env python
"""
builds.py is used to get the primary nightly builds from ftp.mozilla.org, record
the build information and provide that information through the Crash Reporter website.

This script is expected to be run once per day, and will be called from scripts/startBuilds.py.
"""

import logging
import urllib2
from sgmllib import SGMLParser

logger = logging.getLogger("builds")

import socorro.lib.psycopghelper as psy
import socorro.lib.util as util


def buildExists(databaseCursor, product, version, platform, buildid):
  """ Determine whether or not a particular build exists already in the database """
  sql = """
    SELECT * 
    FROM builds
    WHERE product = %s 
    AND version = %s
    AND platform = %s
    AND buildid = %s
  """

  try:
    values = (product, version, platform, buildid)
    build = psy.singleRowSql(databaseCursor, sql, values)
    return True 
  except Exception:
    databaseCursor.connection.rollback()
    logger.info("Did not find build entries in builds table for %s %s %s %s" % (product, version, platform, buildid))
    return None


def fetchBuild(build_url, urllib2=urllib2):
  """ Grab a particular build from the Mozilla FTP site. """
  response = urllib2.urlopen(build_url)
  if response.code == 200:
    data = response.read()
    response.close()
    try: 
      return data.strip().split(" ", 1)
    except Exception:
      util.reportExceptionAndAbort(logger)
      return None
  else: 
    util.reportExceptionAndAbort(logger)
    return None


def insertBuild(databaseCursor, product, version, platform, buildid, changeset, filename):
  """ Insert a particular build into the database """
  build = buildExists(databaseCursor, product, version, platform, buildid)        
  if not build:
    sql = """
      INSERT INTO builds 
      (product, version, platform, buildid, changeset, filename)
      VALUES 
      (%s, %s, %s, %s, %s, %s)
    """ 

    try:
      values = (product, version, platform, buildid, changeset, filename)
      databaseCursor.execute(sql, values) 
      databaseCursor.connection.commit()
      logger.info("Inserted the following build: %s %s %s %s %s %s" % (product, version, platform, buildid, changeset, filename))
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


def fetchTextFiles(config, version, urllib2=urllib2):
  """ Parse the FTP site to find the build information for the latest nightly builds """
  url = "%s%s" % (config.base_url, version)
  try: 
    response = urllib2.urlopen(url)
    if response.code == 200:
      parser = buildParser()
      parser.platforms = config.platforms
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


def fetchAndRecordNightlyBuilds(config, databaseCursor, urllib2=urllib2):
  for version in config.versions:
    builds = fetchTextFiles(config, version, urllib2)
    if builds['builds']:
      for build in builds['builds']:
        build_url = "%s/%s" % (builds['url'], build['filename'])
        build_file = fetchBuild(build_url, urllib2)
        if build_file:
          insertBuild(databaseCursor, build['product'], build['version'], build['platform'], build_file[0], build_file[1], build['filename']) 


def recordNightlyBuilds(config):
  databaseConnectionPool = psy.DatabaseConnectionPool(config.databaseHost, config.databaseName, config.databaseUserName, config.databasePassword, logger)
  try:
    databaseConnection, databaseCursor = databaseConnectionPool.connectionCursorPair()
    fetchAndRecordNightlyBuilds(config, databaseCursor)
  finally:
    databaseConnectionPool.cleanup()

