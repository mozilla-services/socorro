#! /usr/bin/env python
"""
signatureProductdims.py is used to document each of the versions 
in which a crash signature is found.  These will be stored in the 
signature_productsdims table.

This script is expected to be run once per day, and will be called 
from scripts/startProductdims.py.
"""

import datetime
import logging

logger = logging.getLogger("signatureProductdims")

import socorro.lib.psycopghelper as psy
import socorro.lib.util as util


def insertSignatureProductdims(databaseCursor, start_day):
  """
    Populate the signature_productdims table, which will store a list of all of the crash
    signatures associate with each product / version.
  """
  today = datetime.date.today()
  date_start = datetime.datetime(today.year, today.month, today.day - start_day).isoformat(' ')
  date_end = datetime.datetime(today.year, today.month, today.day).isoformat(' ')
  sql = """INSERT INTO signature_productdims
    SELECT
        tcbs.signature,
        tcbs.productdims_id
    FROM top_crashes_by_signature tcbs 
       LEFT OUTER JOIN signature_productdims sd2
       ON sd2.signature = tcbs.signature
       AND sd2.productdims_id = tcbs.productdims_id
    WHERE
        tcbs.window_end > timestamp without time zone '%s'
        AND tcbs.window_end <= timestamp without time zone '%s'
        AND tcbs.signature IS NOT NULL
        AND sd2.signature IS NULL
    GROUP BY     
        tcbs.signature,
        tcbs.productdims_id
  """ % (date_start, date_end)
  logger.info(sql)
  try:
    databaseCursor.execute(sql)
    databaseCursor.connection.commit()
  except Exception,x:
    databaseCursor.connection.rollback()
    util.reportExceptionAndAbort(logger)


def populateSignatureProductdims(config):
  databaseConnectionPool = psy.DatabaseConnectionPool(config.databaseHost, config.databaseName, config.databaseUserName, config.databasePassword, logger)
  try:
    databaseConnection, databaseCursor = databaseConnectionPool.connectionCursorPair()
    insertSignatureProductdims(databaseCursor, config.start_day)
  finally:
    databaseConnectionPool.cleanup()
