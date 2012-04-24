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
