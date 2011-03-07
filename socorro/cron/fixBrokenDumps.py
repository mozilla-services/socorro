#!/usr/bin/python

import time
import sys
import subprocess
import os

import psycopg2
import psycopg2.extras

import socorro.lib.util
import socorro.storage.hbaseClient as hbaseClient

from datetime import datetime

def fetchOoids(configContext, logger, query):
  try:
    databaseDSN = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % configContext
    conn = psycopg2.connect(databaseDSN)
    cur = conn.cursor()
  except:
    socorro.lib.util.reportExceptionAndAbort(logger)


  rows = []
  try:
    before = time.time()
    cur.execute(query)
    rows = cur.fetchall()
    conn.commit()
  except:
    socorro.lib.util.reportExceptionAndAbort(logger)

  return rows

def fix(configContext, logger, query, fixer):
  rows = fetchOoids(configContext, logger, query)
  hbc = hbaseClient.HBaseConnectionForCrashReports(configContext.hbaseHost, configContext.hbasePort, configContext.hbaseTimeout, logger=logger)
  for row in rows:
    try:
      ooid = row[0]
      logger.info('fixing ooid: %s' % ooid)
      dump = hbc.get_dump(ooid)
      fname = '/dev/shm/%s.dump' % ooid
      with open(fname, 'wb') as orig_dump_file:
        orig_dump_file.write(dump)
      logger.debug('wrote dump file: %s' % fname)
      logger.debug('fixed dump file: %s' % fname)
      subprocess.check_call([fixer, fname])
      logger.debug('fixer: %s' % fixer)
      with open(fname, 'rb') as fixed_dump_file:
        fixed_dump = fixed_dump_file.read()
        hbc.put_fixed_dump(ooid, fixed_dump, add_to_unprocessed_queue = True, submitted_timestamp = datetime.now())
      logger.debug('put fixed dump file into hbase: %s' % fname)
      os.unlink(fname)
      logger.debug('removed dump file: %s' % fname)
    except:
      socorro.lib.util.reportExceptionAndContinue(logger)

