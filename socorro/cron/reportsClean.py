# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
from datetime import datetime
from datetime import timedelta

logger = logging.getLogger("reports_clean")

import socorro.lib.psycopghelper as psy
import socorro.lib.util as util

from socorro.lib.datetimeutil import utc_now

#-----------------------------------------------------------------------------------------------------------------
def update_reports_clean(config):
  databaseConnectionPool = psy.DatabaseConnectionPool(config.databaseHost, config.databaseName, config.databaseUserName, config.databasePassword, logger)
  # Set the temp_buffers for this session
  databaseTempbuffers = '8MB' # default
  if 'databaseTempbuffers' in config:
      databaseTempbuffers = config.databaseTempbuffers
  try:
    connection, cursor= databaseConnectionPool.connectionCursorPair()
    cursor.execute(""" SET TEMP_BUFFERS = %s """, (databaseTempbuffers,));
    startTime = utc_now() - timedelta(hours=2)
    cursor.callproc('update_reports_clean', [startTime])
    connection.commit()
  finally:
    databaseConnectionPool.cleanup()

