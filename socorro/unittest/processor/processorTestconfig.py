import socorro.lib.ConfigurationManager as cm
import datetime

databaseHost = cm.Option()
databaseHost.doc = 'the hostname of the database servers'
databaseHost.default = 'localhost'

databaseName = cm.Option()
databaseName.doc = 'the name of the database within the server'
databaseName.default = 'test'

databaseUserName = cm.Option()
databaseUserName.doc = 'the user name for the database servers'
databaseUserName.default = 'test'

databasePassword = cm.Option()
databasePassword.doc = 'the password for the database user'
databasePassword.default = 't3st'

storageRoot = cm.Option()
storageRoot.doc = 'the root of the file system where dumps are found'
storageRoot.default = '%(testDir)s/dumpTest/toBeProcessed/'

deferredStorageRoot = cm.Option()
deferredStorageRoot.doc = 'the root of the file system where dumps are found'
deferredStorageRoot.default = '%(testDir)s/dumpTest/toBeDeferred/'

dumpDirPrefix = cm.Option()
dumpDirPrefix.doc = 'dump directory names begin with this prefix'
dumpDirPrefix.default = 'tst_'

jsonFileSuffix = cm.Option()
jsonFileSuffix.doc = 'the suffix used to identify a json file'
jsonFileSuffix.default = '.json'

dumpFileSuffix = cm.Option()
dumpFileSuffix.doc = 'the suffix used to identify a dump file'
dumpFileSuffix.default = '.dump'

checkForPriorityFrequency = cm.Option()
checkForPriorityFrequency.doc = 'the time bewteen checks for priority jobs (HHH:MM:SS)'
checkForPriorityFrequency.default = '0:01:00'
checkForPriorityFrequency.fromStringConverter = cm.timeDeltaConverter

processorCheckInTime = cm.Option()
processorCheckInTime.doc = 'the time after which a processor is considered dead (HH:MM:SS)'
processorCheckInTime.default = "00:05:00"
processorCheckInTime.fromStringConverter = lambda x: str(cm.timeDeltaConverter(x))

processorCheckInFrequency = cm.Option()
processorCheckInFrequency.doc = 'the frequency in seconds for the processor to check in with the monitor'
processorCheckInFrequency.default = '0:05:00'
processorCheckInFrequency.fromStringConverter = cm.timeDeltaConverter

batchJobLimit = cm.Option()
batchJobLimit.doc = 'the number of jobs to pull in a time'
batchJobLimit.default = 10000

irrelevantSignatureRegEx = cm.Option()
irrelevantSignatureRegEx.doc = 'a regular expression matching frame signatures that should be ignored when generating an overall signature'
irrelevantSignatureRegEx.default = '@0x[01234567890abcdefABCDEF]{2,}'

prefixSignatureRegEx = cm.Option()
prefixSignatureRegEx.doc = 'a regular expression matching frame signatures that should always be coupled with the following frame signature when generating an overall signature'
prefixSignatureRegEx.default = '@0x0|strchr|strstr|strcmp|memcpy|memcmp|malloc|realloc|.*free|arena_dalloc_small|nsObjCExceptionLogAbort\(.*?\)|nsCOMPtr_base::assign_from_qi(nsQueryInterface, nsID const&)'

processorLoopTime = cm.Option()
processorLoopTime.doc = 'the time to wait between attempts to get jobs (HHH:MM:SS)'
processorLoopTime.default = '0:00:06'
processorLoopTime.fromStringConverter = cm.timeDeltaConverter

numberOfThreads = cm.Option()
numberOfThreads.doc = 'the number of threads to use'
numberOfThreads.default = 4

processorId = cm.Option()
processorId.doc = 'the id number for the processor (must already exist in database) (0 for create new Id, "auto" for autodetection)'
processorId.default = "auto"

processorSymbolsPathnameList = cm.Option()
processorSymbolsPathnameList.doc = 'comma or space separated list of symbol files for minidump_stackwalk (quote paths with embedded spaces)'
processorSymbolsPathnameList.default = "/mnt/socorro/symbols/symbols_ffx,/mnt/socorro/symbols/symbols_sea,/mnt/socorro/symbols/symbols_tbrd,/mnt/socorro/symbols/symbols_sbrd,/mnt/socorro/symbols/symbols_os"
processorSymbolsPathnameList.fromStringConverter = lambda x: x.replace(',', ' ')

crashingThreadFrameThreshold = cm.Option()
crashingThreadFrameThreshold.doc = "the number of frames to keep in the raw dump for the crashing thread"
crashingThreadFrameThreshold.default = 100

crashingThreadTailFrameThreshold = cm.Option()
crashingThreadTailFrameThreshold.doc="the number of frames to keep in the raw dump at the tail of the frame list"
crashingThreadTailFrameThreshold.default = 10

stackwalkCommandLine = cm.Option()
stackwalkCommandLine.doc = 'the template for the command to invoke minidump_stackwalk'
#for standard minidump_stackwalk uncomment this line:
stackwalkCommandLine.default = '$minidump_stackwalkPathname -m $dumpfilePathname $processorSymbolsPathnameList 2>/dev/null'
#for caching minidump_stackwalk uncomment this line:
#stackwalkCommandLine.default = '$minidump_stackwalkPathname -c $symbolCachePath  -m $dumpfilePathname $processorSymbolsPathnameList 2>/dev/null'

minidump_stackwalkPathname = cm.Option()
minidump_stackwalkPathname.doc = 'the full pathname of the extern program minidump_stackwalk (quote path with embedded spaces)'
minidump_stackwalkPathname.default = '/usr/local/bin/minidump_stackwalk'

logFilePathname = cm.Option()
logFilePathname.doc = 'full pathname for the log file'
logFilePathname.default = '%(testDir)s/logs/processor_test.log'

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
stderrErrorLoggingLevel.default = 40

