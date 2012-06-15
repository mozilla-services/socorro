## Test config file for database utilities
import socorro.lib.ConfigurationManager as cm
import datetime

from socorro.unittest.config.commonconfig import databaseHost
from socorro.unittest.config.commonconfig import databaseName
from socorro.unittest.config.commonconfig import databaseUserName
from socorro.unittest.config.commonconfig import databasePassword

logFilePathname = cm.Option()
logFilePathname.doc = 'full pathname for the log file'
logFilePathname.default = '%(testDir)s/logs/db_test.log'

