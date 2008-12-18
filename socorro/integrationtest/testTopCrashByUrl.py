#! /usr/bin/env python

import unittest
from socorrotestcase import SocorroTestCase

import logging
import logging.handlers
import sys
import time


import psycopg2
import psycopg2.extras

try:
  import config.topcrashbyurlconfig as config
except ImportError:
  import topcrashbyurlconfig as config

import socorro.lib.ConfigurationManager as configurationManager
import socorro.cron.topcrashbyurl as tcbyurl

class TestTopCrashByUrl(SocorroTestCase):
  def setUp(self):
    configContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Top Crash By URL Summary")
    logger = logging.getLogger("tcbyurl_summary")
    logger.setLevel(logging.DEBUG)
    stderrLog = logging.StreamHandler()
    stderrLog.setLevel(configContext.stderrErrorLoggingLevel)
    stderrLogFormatter = logging.Formatter(configContext.stderrLineFormatString)
    stderrLog.setFormatter(stderrLogFormatter)
    logger.addHandler(stderrLog)
    rotatingFileLog = logging.handlers.RotatingFileHandler(configContext.logFilePathname, "a", configContext.logFileMaximumSize, configContext.logFileMaximumBackupHistory)
    rotatingFileLog.setLevel(logging.DEBUG)
    rotatingFileLogFormatter = logging.Formatter(configContext.logFileLineFormatString)
    rotatingFileLog.setFormatter(rotatingFileLogFormatter)
    logger.addHandler(rotatingFileLog)
    logger.info("current configuration\n%s", str(configContext))


    self.configContext = configContext
    self.logger = logger
    self.rotatingFileLog = rotatingFileLog

  def testIntegration(self):
    logger = self.logger
    try:
      databaseDSN = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % self.configContext
      conn = psycopg2.connect(databaseDSN)
      cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)      

      logger.info("CLEANING OUT facts and dimension tables")
      cur.execute("DELETE FROM topcrashurlfacts")
      cur.execute("DELETE FROM urldims")
      cur.execute("DELETE FROM signaturedims WHERE id != 1")
      conn.commit()

      staticDims = {'signature_id': 1, 'product_id': 6, 'product_name': 'Firefox', 'product_version': '3.0.1', 'start_date':'2008-09-16 00:00:00', 'end_date':'2008-09-16 23:59:59', 'date':'2008-09-16'}
      tcbyurl.populateFactsForDim(tcbyurl.ByUrlDomain(), staticDims, conn, cur, logger)

      self.checkDomainDimension(cur, conn, logger)
      self.checkCrashesByDomain(cur, conn, logger)

      tcbyurl.populateFactsForDim(tcbyurl.ByUrlEachUrl(), staticDims, conn, cur, logger)
      self.checkUrlDimension(cur, conn, logger)
      self.checkCrashesByUrl(cur, conn, logger)
      self.checkUrlDimGoogleFr(cur, conn, logger)

      del staticDims['signature_id']
      staticDims['urldims_id']  = self.getGoogleDotComUrlId(cur)
      staticDims['urldims_url'] = 'http://www.google.com/'

      tcbyurl.populateFactsForDim(tcbyurl.BySignature(), staticDims, conn, cur, logger)

      self.checkSignatureDimension(cur, conn, logger)
      self.checkSignatureFactsGoogle(cur, conn, logger)
    finally:
      self.rotatingFileLog.flush()
      self.rotatingFileLog.close()

  def getGoogleDotComUrlId(self, cur):
      cur.execute("SELECT id FROM urldims WHERE url = 'http://www.google.com/'")
      urlId = cur.fetchone()['id']
      self.assertTrue( int(urlId) > 0, "Unable to run integration tests, can't find test url's id in dimension table... %s" % (urlId))
      return urlId

  def checkSignatureFactsGoogle(self, cur, conn, logger):
    sql = """
    SELECT SUM(count) as count, signaturedims.signature
    FROM topcrashurlfacts AS facts 
    JOIN signaturedims ON facts.signature_fk = signaturedims.id
    JOIN urldims ON facts.urldims_fk = urldims.id
    WHERE '2008-09-15' <= day AND day <= '2008-09-20'
    AND urldims.url = 'http://www.google.com/'
    AND signaturedims.id != 1
    GROUP BY signature
    ORDER BY count DESC """
    cur.execute(sql)
    row = cur.fetchone()
    self.assertEquals(5, row['count'], "Google.com should have 50 @0xfffeff20 crashef20 crashes, but has %s" % (row['count']))
    self.assertEquals('@0xfffeff20', row['signature'], "@0xfffef is the most common crash ignature... but was %s" % (row['signature']))

  def checkSignatureDimension(self, cur, conn, logger):
    cur.execute("SELECT count(id) AS count FROM signaturedims")
    actual = cur.fetchone()['count']
    self.assertEqual(21, actual, "We should have some signatues in dimension table... we have %s" % (actual))
    cur.execute("SELECT id, signature FROM signaturedims WHERE signature IN ('fastzero_I')")
    actual = cur.fetchall()
    self.assertEqual(1, len(actual), "We should have only 1 fastzero_I signatues.. we have %s" % (actual))

  def checkCrashesByDomain(self, cur, conn, logger):
    sql = """SELECT * FROM topcrashurlfacts AS facts
             JOIN urldims AS u ON facts.urldims_fk = u.id
             WHERE u.url = 'ALL'
             ORDER BY count DESC
             LIMIT 10;"""
    cur.execute(sql)
    row = cur.fetchone()
    self.assertEqual(196, row['count'])
    self.assertEqual(1, row['rank'])
    self.assertEqual("www.google.com", row['domain'])
    logger.info("huh that's weird that this passed %s" % (row))

  def checkCrashesByUrl(self, cur, conn, logger):
    sql = """SELECT * FROM topcrashurlfacts AS facts
             JOIN urldims AS u ON facts.urldims_fk = u.id
             WHERE u.url != 'ALL'
             ORDER BY count DESC
             LIMIT 10;"""
    cur.execute(sql)
    row = cur.fetchone()
    self.assertEqual(42, row['count'])
    self.assertEqual(1, row['rank'])
    self.assertEqual("http://www.google.com/firefox", row['url'])

  def checkDomainDimension(self, cur, conn, logger):
    sql = "SELECT count(id) from urldims WHERE url = 'ALL';"
    cur.execute(sql)
    self.assertEqual(1, cur.rowcount, "We expect some data")
    actual = cur.fetchone()['count']
    self.assertEqual(3321, actual, "The number of domains in dataset %s" % (actual))

  def checkUrlDimension(self, cur, conn, logger):
    sql = "SELECT count(id) from urldims WHERE url != 'ALL';"
    cur.execute(sql)
    self.assertEqual(1, cur.rowcount, "We expect some data")
    actual = cur.fetchone()['count']
    self.assertEqual(4069, actual, "The number of urls in dataset %s" % (actual))

  def checkUrlDimGoogleFr(self, cur, conn, logger):
    sql = """SELECT SUM(count) FROM topcrashurlfacts
             JOIN urldims AS u ON topcrashurlfacts.urldims_fk = u.id
             WHERE u.url != 'ALL' AND u.domain = 'www.google.fr';"""
    cur.execute(sql)
    self.assertEqual(1, cur.rowcount, "We expect some data")
    actual = cur.fetchone()['sum']
    self.assertEqual(42, actual, "The sum of google.fr url crashes %s" % (actual))

if __name__ == "__main__":
  unittest.main()
