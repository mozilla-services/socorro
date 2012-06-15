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

logFilePathname = cm.Option()
logFilePathname.doc = 'full pathname for the log file'
logFilePathname.default = '%(testDir)s/logs/lib_test.log'

logFileMaximumSize = cm.Option()
logFileMaximumSize.doc = 'maximum size in bytes of the log file'
logFileMaximumSize.default = 1000000

logFileMaximumBackupHistory = cm.Option()
logFileMaximumBackupHistory.doc = 'maximum number of log files to keep'
logFileMaximumBackupHistory.default = 50

logFileLineFormatString = cm.Option()
logFileLineFormatString.doc = 'python logging system format for log file entries'
logFileLineFormatString.default = '%(asctime)s %(levelname)s - %(message)s'

logFileErrorLoggingLevel = cm.Option()
logFileErrorLoggingLevel.doc = 'logging level for the log file (10 - DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR, 50 - CRITICAL)'
logFileErrorLoggingLevel.default = 10

#syslogHost = cm.Option()
#syslogHost.doc = 'syslog hostname'
#syslogHost.default = 'localhost'

#syslogPort = cm.Option()
#syslogPort.doc = 'syslog port'
#syslogPort.default = 514

#syslogFacilityString = cm.Option()
#syslogFacilityString.doc = 'syslog facility string ("user", "local0", etc)'
#syslogFacilityString.default = 'user'

#syslogLineFormatString = cm.Option()
#syslogLineFormatString.doc = 'python logging system format for syslog entries'
#syslogLineFormatString.default = 'Socorro (pid %(process)d): %(asctime)s %(levelname)s - %(threadName)s - %(message)s'

#syslogErrorLoggingLevel = cm.Option()
#syslogErrorLoggingLevel.doc = 'logging level for the log file (10 - DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR, 50 - CRITICAL)'
#syslogErrorLoggingLevel.default = 10


stderrLineFormatString = cm.Option()
stderrLineFormatString.doc = 'python logging system format for logging to stderr'
stderrLineFormatString.default = '%(asctime)s %(levelname)s - %(message)s'

stderrErrorLoggingLevel = cm.Option()
stderrErrorLoggingLevel.doc = 'logging level for the logging to stderr (10 - DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR, 50 - CRITICAL)'
stderrErrorLoggingLevel.default = 40

