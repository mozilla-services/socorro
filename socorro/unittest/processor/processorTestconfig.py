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

#processedDumpStoragePath = cm.Option()
#processedDumpStoragePath.doc = 'the path of the file system where processed dumps are stored'
#processedDumpStoragePath.default = '%(testDir)s/dumpTest/processedDumps'

#dumpDirPrefix = cm.Option()
#dumpDirPrefix.doc = 'dump directory names begin with this prefix'
#dumpDirPrefix.default = 'tst_'

elasticSearchOoidSubmissionUrl = cm.Option()
elasticSearchOoidSubmissionUrl.doc = 'a url to submit ooids for Elastic Search (use %s in place of the ooid) (leave blank for no Elastic Search)'
elasticSearchOoidSubmissionUrl.default = '%s'

temporaryFileSystemStoragePath = cm.Option()
temporaryFileSystemStoragePath.doc = 'a local filesystem path where processor can write dumps temporarily for processing'
temporaryFileSystemStoragePath.default = './'

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

signatureSentinels = cm.Option()
signatureSentinels.doc = 'a list of frame signatures that should always be considered top of the stack if present in the stack'
signatureSentinels.default = ['sentinel_1', 'sentinel_2']

irrelevantSignatureRegEx = cm.Option()
irrelevantSignatureRegEx.doc = 'a regular expression matching frame signatures that should be ignored when generating an overall signature'
irrelevantSignatureRegEx.default = '@0x[01234567890abcdefABCDEF]{2,}'

prefixSignatureRegEx = cm.Option()
prefixSignatureRegEx.doc = 'a regular expression matching frame signatures that should always be coupled with the following frame signature when generating an overall signature'
prefixSignatureRegEx.default = '@0x0|strchr|strstr|strcmp|memcpy|memcmp|malloc|realloc|.*free|arena_dalloc_small|nsObjCExceptionLogAbort\(.*?\)|nsCOMPtr_base::assign_from_qi(nsQueryInterface, nsID const&)'

signaturesWithLineNumbersRegEx = cm.Option()
signaturesWithLineNumbersRegEx.doc = 'any signatures that match this list should be combined with their associated source code line numbers'
signaturesWithLineNumbersRegEx.default = 'js_Interpret'

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

collectAddon = cm.Option()
collectAddon.doc = "if true, parse and collect information about addons from the json file; if false, don't"
collectAddon.default = False
collectAddon.fromStringConverter = cm.booleanConverter

collectCrashProcess = cm.Option()
collectCrashProcess.doc = "if true, parse and collect information about out of process crashes; if false, don't"
collectCrashProcess.default = True
collectCrashProcess.fromStringConverter = cm.booleanConverter

dumpPermissions = cm.Option()
dumpPermissions.doc = 'when saving processed dumps, the pemission flags to be used'
dumpPermissions.default = '%d'%(stat.S_IRGRP | stat.S_IWGRP | stat.S_IRUSR | stat.S_IWUSR)

dirPermissions = cm.Option()
dirPermissions.doc = 'when saving processed dumps, the pemission flags to be used on directories'
dirPermissions.default = '%d'%(stat.S_IRGRP | stat.S_IXGRP | stat.S_IWGRP | stat.S_IRUSR | stat.S_IXUSR | stat.S_IWUSR)

dumpGID = cm.Option()
dumpGID.doc = 'when saving processed dumps, the group to save the files under (leave blank for file system default)'
dumpGID.default = ''

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

