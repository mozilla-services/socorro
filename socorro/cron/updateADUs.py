# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import datetime

logger = logging.getLogger("updateADUs")

import psycopg2
import socorro.lib.psycopghelper as psy
import socorro.lib.util as util

from socorro.lib.datetimeutil import utc_now

def update_adus(config):
  databaseConnectionPool = psy.DatabaseConnectionPool(config.databaseHost,
      config.databaseName, config.databaseUserName, config.databasePassword,
      logger)
  # Set the temp_buffers for this session
  databaseTempbuffers = '8MB' # default
  if 'databaseTempbuffers' in config:
    databaseTempbuffers = config.databaseTempbuffers
  try:
    connection, cursor = databaseConnectionPool.connectionCursorPair()

    cursor.execute(""" SET TEMP_BUFFERS = %s """, (databaseTempbuffers,));
    startTime = (utc_now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    cursor.callproc('update_adu', [startTime])
    connection.commit()
  except psycopg2.InternalError, e:
    errmsg = 'ERROR:  update_adu has already been run for %s\n' % (startTime)
    if e.pgerror == errmsg:
      logger.warn('Update ADU already run for %s, ignoring' % (startTime))
    else:
      raise
  finally:
    databaseConnectionPool.cleanup()

