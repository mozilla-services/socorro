# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

## Test config file for testMtbf
import socorro.lib.ConfigurationManager as cm
import datetime

from socorro.unittest.config.commonconfig import databaseHost
try:
  from socorro.unittest.config.commonconfig import databasePort
except:
  databasePort = 5432
from socorro.unittest.config.commonconfig import oldDatabaseName as databaseName
from socorro.unittest.config.commonconfig import databaseUserName
from socorro.unittest.config.commonconfig import databasePassword

# processingDay = cm.Option()
# processingDay.doc = 'Day to process in (YYYY-MM-DD) format'
# processingDay.default = (datetime.date.today() - datetime.timedelta(1)).isoformat() # yesterday
# processingDay.singleCharacter = 'd'

logFilePathname = cm.Option()
logFilePathname.doc = 'full pathname for the log file'
logFilePathname.default = '%(testDir)s/logs/cron_test.log'
