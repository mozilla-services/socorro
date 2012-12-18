#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import time
import sys
import subprocess
import os
import cPickle

import psycopg2
import psycopg2.extras

import socorro.lib.util
import socorro.storage.hbaseClient as hbaseClient
from socorro.lib.datetimeutil import date_to_string

from datetime import datetime, timedelta

from socorro.lib.datetimeutil import utc_now

def fetchOoids(configContext, logger, query):
  try:
    databaseDSN = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % configContext
    conn = psycopg2.connect(databaseDSN)
    cur = conn.cursor()
  except:
    socorro.lib.util.reportExceptionAndAbort(logger)

  last_date_processed = get_last_run_date(configContext)

  rows = []
  try:
    before = time.time()
    logger.debug('last_date_processed used for query: %s' % last_date_processed)
    cur.execute(query % last_date_processed)
    rows = cur.fetchall()
    conn.commit()
  except:
    socorro.lib.util.reportExceptionAndAbort(logger)

  return rows, last_date_processed

def fix(configContext, logger, query, fixer):
  rows, last_date_processed = fetchOoids(configContext, logger, query)
  hbc = hbaseClient.HBaseConnectionForCrashReports(configContext.hbaseHost, configContext.hbasePort, configContext.hbaseTimeout, logger=logger)
  for row in rows:
    try:
      ooid, last_date_processed = row
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
        hbc.put_fixed_dump(ooid, fixed_dump, add_to_unprocessed_queue = True, submitted_timestamp = date_to_string(utc_now())
      logger.debug('put fixed dump file into hbase: %s' % fname)
      os.unlink(fname)
      logger.debug('removed dump file: %s' % fname)
    except:
      socorro.lib.util.reportExceptionAndContinue(logger)

  return last_date_processed

def get_last_run_date(config):
  try:
    with open(config.persistentBrokenDumpPathname, 'r') as f:
      return cPickle.load(f)
  except IOError:
    return utc_now() - timedelta(days=config.daysIntoPast)

def save_last_run_date(config, date):
  with open(config.persistentBrokenDumpPathname, 'w') as f:
    return cPickle.dump(date, f)

