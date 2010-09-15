import socorro.lib.util as util
import socorro.storage.crashstorage as cstore

def start(config):
  assert 'processorHostNames' in config, "'processorHostNames' missing from config"
  assert 'resubmitTimeDeltaThreshold' in config, "'resubmitTimeDeltaThreshold' missing from config"
  crashStoragePool = cstore.CrashStoragePool(config)
  try:
    crashStorage = crashStoragePool.crashStorage()
    hbaseConnection = crashStorage.hbaseConnection
    hbaseConnection.submit_to_processor(config.processorHostNames,
                                        resubmitTimeDeltaThreshold=config.resubmitTimeDeltaThreshold)
  finally:
    crashStorage.close()


