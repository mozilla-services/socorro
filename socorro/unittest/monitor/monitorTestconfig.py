# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import socorro.lib.ConfigurationManager as cm
import stat

from socorro.unittest.config.commonconfig import databaseHost
try:
  from socorro.unittest.config.commonconfig import databasePort
except:
  databasePort = 5432
from socorro.unittest.config.commonconfig import databaseName
from socorro.unittest.config.commonconfig import databaseUserName
from socorro.unittest.config.commonconfig import databasePassword

from socorro.unittest.config.commonconfig import hbaseHost
from socorro.unittest.config.commonconfig import hbasePort
from socorro.unittest.config.commonconfig import hbaseTimeout

#storageRoot = cm.Option()
#storageRoot.doc = 'the root of the file system where dumps are found'
#storageRoot.default = '%(testDir)s/dumpTest/toBeProcessed/'

#deferredStorageRoot = cm.Option()
#deferredStorageRoot.doc = 'the root of the file system where dumps are found'
#deferredStorageRoot.default = '%(testDir)s/dumpTest/toBeDeferred/'

#bigStorageRoot = cm.Option()
#bigStorageRoot.doc = 'the root of the file system where big test set is found'
#bigStorageRoot.default = '%(testDir)s/testdata'

#dumpDirPrefix = cm.Option()
#dumpDirPrefix.doc = 'dump directory names begin with this prefix'
#dumpDirPrefix.default = 'tst_'

#jsonFileSuffix = cm.Option()
#jsonFileSuffix.doc = 'the suffix used to identify a json file'
#jsonFileSuffix.default = '.json'

#dumpFileSuffix = cm.Option()
#dumpFileSuffix.doc = 'the suffix used to identify a dump file'
#dumpFileSuffix.default = '.dump'

processorCheckInTime = cm.Option()
processorCheckInTime.doc = 'the time after which a processor is considered dead (HH:MM:SS)'
processorCheckInTime.default = "00:05:00"
processorCheckInTime.fromStringConverter = lambda x: str(cm.timeDeltaConverter(x))

standardLoopDelay = cm.Option()
standardLoopDelay.doc = 'the time between scans for jobs (HHH:MM:SS)'
standardLoopDelay.default = '00:05:00'
standardLoopDelay.fromStringConverter = cm.timeDeltaConverter

cleanupJobsLoopDelay = cm.Option()
cleanupJobsLoopDelay.doc = 'the time between runs of the job clean up routines (HHH:MM:SS)'
cleanupJobsLoopDelay.default = '00:05:00'
cleanupJobsLoopDelay.fromStringConverter = cm.timeDeltaConverter

priorityLoopDelay = cm.Option()
priorityLoopDelay.doc = 'the time between checks for priority jobs (HHH:MM:SS)'
priorityLoopDelay.default = '00:01:00'
priorityLoopDelay.fromStringConverter = cm.timeDeltaConverter

#saveSuccessfulMinidumpsTo = cm.Option()
#saveSuccessfulMinidumpsTo.doc = 'the location for saving successfully processed dumps (leave blank to delete them instead)'
#saveSuccessfulMinidumpsTo.default = '%(testDir)s/dumpTest/socorro-sucessful'

#saveFailedMinidumpsTo = cm.Option()
#saveFailedMinidumpsTo.doc = 'the location for saving dumps that failed processing (leave blank to delete them instead)'
#saveFailedMinidumpsTo.default = '%(testDir)s/dumpTest/socorro-failed'

#dumpPermissions = cm.Option()
#dumpPermissions.doc = 'when saving dumps, the pemission flags to be used'
#dumpPermissions.default = '%d'%(stat.S_IRGRP | stat.S_IWGRP | stat.S_IRUSR | stat.S_IWUSR)

#dirPermissions = cm.Option()
#dirPermissions.doc = 'when saving dumps, the pemission flags to be used on directories'
#dirPermissions.default = '%d'%(stat.S_IRGRP | stat.S_IXGRP | stat.S_IWGRP | stat.S_IRUSR | stat.S_IXUSR | stat.S_IWUSR)

#dumpGID = cm.Option()
#dumpGID.doc = 'when saving dumps, the group to save the files under (leave blank for file system default)'
#dumpGID.default = ''

logFilePathname = cm.Option()
logFilePathname.doc = 'full pathname for the log file'
logFilePathname.default = '%(testDir)s/logs/monitor_test.log'

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

stderrLineFormatString = cm.Option()
stderrLineFormatString.doc = 'python logging system format for logging to stderr'
stderrLineFormatString.default = '%(asctime)s %(levelname)s - %(message)s'

stderrErrorLoggingLevel = cm.Option()
stderrErrorLoggingLevel.doc = 'logging level for the logging to stderr (10 - DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR, 50 - CRITICAL)'
stderrErrorLoggingLevel.default = 10

