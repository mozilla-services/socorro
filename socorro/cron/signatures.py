#! /usr/bin/env python
"""
signatures.py calls a stored procedure used for updating the first appearance
of signature information, as well as updating signature_productdims.  

This script is expected to be run once per hour, and will be called 
from scripts/startSignatures.py.
"""

from datetime import datetime
from datetime import timedelta
import logging

logger = logging.getLogger("signatures")

import socorro.lib.psycopghelper as psy
import socorro.lib.util as util

def update_signatures(config):
  databaseConnectionPool = psy.DatabaseConnectionPool(config.databaseHost, config.databaseName, config.databaseUserName, config.databasePassword, logger)
  try:
    databaseConnection, databaseCursor = databaseConnectionPool.connectionCursorPair()
    databaseCursor.execute("""
    SELECT max(first_report) FROM signature_build
    """);
    last_run = databaseCursor.fetchone()[0]
    now = datetime.now()
    delta = now - last_run
    total_seconds = delta.days * 86400 + delta.seconds
    total_hours = total_seconds / 3600
    logger.info("total_hours: %s" % total_hours)
    for hour in xrange(total_hours):
      hour = int(hour) + 1
      timestamp = now - timedelta(hours=hour)
      databaseCursor.execute("""
        --- time, hours_back, hours_window
        SELECT update_signature_matviews('%s', 3, 2)
      """ % (timestamp))
      databaseConnection.commit()
  finally:
    databaseConnectionPool.cleanup()
