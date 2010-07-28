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
    logger.info("Did not find build entries in builds table for %s %s %s %s" % (product, version, platform, buildid))
    return None


def fetchBuild(build_url, urllib2=urllib2):
  """ Grab a particular build from the Mozilla FTP site. """
  response = urllib2.urlopen(build_url)
  if response.code == 200:
    data = response.read()
    response.close()
    try: 
      return data.strip().split(" ")
    except Exception:
      util.reportExceptionAndAbort(logger)
      return None
  else: 
    util.reportExceptionAndAbort(logger)
    return None


def insertBuild(databaseCursor, product, version, platform, buildid, platform_changeset, app_changeset_1, app_changeset_2, filename):
  """ Insert a particular build into the database """
  build = buildExists(databaseCursor, product, version, platform, buildid)        
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


def fetchTextFiles(config, product_uri, urllib2=urllib2):
  """ Parse the FTP site to find the build information for the latest nightly builds """
  url = "%s%s" % (config.base_url, product_uri)
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
  for product_uri in config.product_uris:
    builds = fetchTextFiles(config, product_uri, urllib2)
    if builds['builds']:
      for build in builds['builds']:
        build_url = "%s%s" % (builds['url'], build['filename'])
        build_file = fetchBuild(build_url, urllib2)
        if build_file:
          buildid = build_file[0]
          platform_changeset = '' 
          app_changeset_1 = ''
          app_changeset_2 = ''

          try:
            if build_file[1]:
              platform_changeset = os.path.basename(build_file[1])
          except Exception:
            util.reportExceptionAndContinue(logger, 30)
          try:
            if build_file[2]:
              app_changeset_1 = os.path.basename(build_file[2])
          except Exception:
            util.reportExceptionAndContinue(logger, 30)
          try:
            if build_file[3]:
              app_changeset_2 = os.path.basename(build_file[3])
          except Exception:
            util.reportExceptionAndContinue(logger, 30)
 
          insertBuild(databaseCursor, build['product'], build['version'], build['platform'], buildid, platform_changeset, app_changeset_1, app_changeset_2, build['filename']) 


def recordNightlyBuilds(config):
  databaseConnectionPool = psy.DatabaseConnectionPool(config.databaseHost, config.databaseName, config.databaseUserName, config.databasePassword, logger)
  try:
    databaseConnection, databaseCursor = databaseConnectionPool.connectionCursorPair()
    fetchAndRecordNightlyBuilds(config, databaseCursor)
  finally:
    databaseConnectionPool.cleanup()

