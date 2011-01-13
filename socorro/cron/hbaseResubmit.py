try:
  import json
except ImportError:
  import simplejson as json

import socorro.lib.JsonDumpStorage as jds
import socorro.storage.hbaseClient as hbc
import socorro.lib.util as sutil
import socorro.lib.datetimeutil as dtutil


def resubmit (conf, jds=jds, hbc=hbc, open=open):
  logger = conf.logger
  logger.info('creating hbase connection: host: %s, port: %s', conf.hbaseHost, conf.hbasePort)
  hbaseConnection = hbc.HBaseConnectionForCrashReports(conf.hbaseHost,
                                                       conf.hbasePort,
                                                       conf.hbaseTimeout)
  logger.info('creating json/dump store object: root: %s', conf.hbaseFallbackFS)
  fallbackStorage = jds.JsonDumpStorage(root=conf.hbaseFallbackFS,
                                        maxDirectoryEntries = conf.hbaseFallbackDumpDirCount,
                                        jsonSuffix = conf.jsonFileSuffix,
                                        dumpSuffix = conf.dumpFileSuffix,
                                        dumpGID = conf.hbaseFallbackDumpGID,
                                        dumpPermissions = conf.hbaseFallbackDumpPermissions,
                                        dirPermissions = conf.hbaseFallbackDirPermissions,
                                       )
  processedCrashList = []
  for uuid in fallbackStorage.destructiveDateWalk():
    logger.info('found uuid: %s', uuid)
    try:
      jsonFile = open(fallbackStorage.getJson(uuid))
      try:
        jsonContents = json.load(jsonFile)
      finally:
        jsonFile.close()
      dumpFile = open(fallbackStorage.getDump(uuid))
      try:
        dumpContents = dumpFile.read()
      finally:
        dumpFile.close()
      logger.debug('pushing %s to hbase', uuid)
      hbaseConnection.put_json_dump(uuid, jsonContents, dumpContents)
      processedCrashList.append(uuid)
    except Exception, x:
      sutil.reportExceptionAndContinue(logger)

  logger.info('cleanup fallback filesystem')
  for uuid in processedCrashList:
    fallbackStorage.remove(uuid)



# the following code is for a theorectical system that would be able
# to scan through a set of days in hbase and placement of crashes
# in the 2009 style JsonDumpStorage for processing.
# specifically in response to Bug 552539


import socorro.collector.crashstorage as cstore
import socorro.lib.JsonDumpStorage as jds
import socorro.lib.datetimeutil as dtu

def yearMonthDayTuple(dateAsString):
  dateAsString = dateAsString.strip()
  date = dtutil.datetimeFromISOdateString(dateAsString)
  return date.year, date.month, date.day

def uuidIn(ooid, fileSystemStorageTuple):
  for aJsonStorage in fileSystemStorageTuple:
    try:
      aJsonStorage.getJson(ooid)
      return True
    except Exception:
      pass
  return False

def hbaseToNfsResubmit(conf, hbc=hbc, open=open):
  logger = conf.logger
  logger.info('creating hbase connection: host: %s, port: %s', conf.hbaseHost, conf.hbasePort)
  hbaseConnection = hbc.HBaseConnectionForCrashReports(conf.hbaseHost, conf.hbasePort)

  nfsStorage = cstore.CrashStorageSystemForNFS(conf)

  stdStorage = jds.JsonDumpStorage(root = conf.storageRoot,
                                   maxDirectoryEntries = conf.dumpDirCount,
                                   jsonSuffix = conf.jsonFileSuffix,
                                   dumpSuffix = conf.dumpFileSuffix,
                                   dumpGID = conf.dumpGID,
                                   dumpPermissions = conf.dumpPermissions,
                                   dirPermissions = conf.dirPermissions,
                                   logger = conf.logger
                                  )
  defStorage = jds.JsonDumpStorage(root = conf.deferredStorageRoot,
                                   maxDirectoryEntries = conf.dumpDirCount,
                                   jsonSuffix = conf.jsonFileSuffix,
                                   dumpSuffix = conf.dumpFileSuffix,
                                   dumpGID = conf.dumpGID,
                                   dumpPermissions = conf.dumpPermissions,
                                   dirPermissions = conf.dirPermissions,
                                   logger = conf.logger
                                  )
  sucStorage = jds.JsonDumpStorage(root = conf.saveSuccessfulMinidumpsTo,
                                   maxDirectoryEntries = conf.dumpDirCount,
                                   jsonSuffix = conf.jsonFileSuffix,
                                   dumpSuffix = conf.dumpFileSuffix,
                                   dumpPermissions = conf.dumpPermissions,
                                   dirPermissions = conf.dirPermissions,
                                   dumpGID = conf.dumpGID,
                                   logger = conf.logger
                                  )

  fileSystemStorageTuple = (stdStorage, defStorage, sucStorage)

  compressedDateList = [ ('%4d%02d%02d' % yearMonthDayTuple(x))[2:] for x in conf.resubmissionDateList.split(',')]

  for aDate in compressedDateList:
    logger.debug('trying for date "%s"', aDate)
    for aCrash in hbaseConnection.scan_starting_with(aDate, 4):
      ooid = aCrash['ooid']
      if not uuidIn(ooid, fileSystemStorageTuple):
        jsonData = sutil.DotDict(hbaseConnection.get_json(ooid))
        try:
          timestamp = dtu.datetimeFromISOdateString(jsonData['submitted_timestamp'])
          logger.debug('%s should be inserted', ooid)
          dump = hbaseConnection.get_dump(ooid)
          logger.debug('   saving...')
          nfsStorage.save(ooid, jsonData, dump, timestamp)
        except Exception:
          sutil.reportExceptionAndContinue(conf.logger)
      else:
        logger.debug('skipping %s', ooid)



