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
  sql = """
    --- time, hours_back, hours_window
    SELECT update_signature_matviews('%s', 3, 2)
  """
  try:
    databaseConnection, databaseCursor = databaseConnectionPool.connectionCursorPair()
    databaseCursor.execute(sql % (datetime.now()))
    databaseConnection.commit()
  finally:
    databaseConnectionPool.cleanup()
