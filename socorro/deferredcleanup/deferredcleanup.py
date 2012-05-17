# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime as dt

import socorro.lib.JsonDumpStorage as jds
import socorro.lib.util
from socorro.lib.datetimeutil import utc_now

def deferredJobStorageCleanup (config, logger):
  """
  """
  try:
    logger.info("beginning deferredJobCleanup")
    j = jds.JsonDumpStorage(root = config.deferredStorageRoot)
    numberOfDaysAsTimeDelta = dt.timedelta(days=int(config.maximumDeferredJobAge))
    threshold = utc_now() - numberOfDaysAsTimeDelta
    logger.info("  removing older than: %s", threshold)
    j.removeOlderThan(threshold)
  except (KeyboardInterrupt, SystemExit):
    logger.debug("got quit message")
  except:
    socorro.lib.util.reportExceptionAndContinue(logger)
  logger.info("deferredJobCleanupLoop done.")



