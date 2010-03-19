import socorro.cron.hbaseResubmit as hbr
import socorro.lib.util as util
import socorro.unittest.testlib.expectations as exp

def testResubmit ():
  conf = util.DotDict()
  jds_kwargs = util.DotDict()
  conf.logger = util.SilentFakeLogger()
  #conf.logger = util.FakeLogger()
  conf.hbaseHost = 'fred'
  conf.hbasePort = 666
  jds_kwargs.root = conf.hbaseFallbackFS = '.'
  jds_kwargs.maxDirectoryEntries = conf.dumpDirCount = 100000
  jds_kwargs.jsonSuffix = conf.jsonFileSuffix = 'json'
  jds_kwargs.dumpSuffix = conf.dumpFileSuffix = 'dump'
  jds_kwargs.dumpGID = conf.dumpGID = 'lucy'
  jds_kwargs.dumpPermissions = conf.dumpPermissions = 660
  jds_kwargs.dirPermissions = conf.dirPermissions = 770

  fakeHbaseConnection  = exp.DummyObjectWithExpectations()
  fakeHbaseModule = exp.DummyObjectWithExpectations()
  fakeHbaseModule.expect('HBaseConnectionForCrashReports', (conf.hbaseHost, conf.hbasePort), {}, fakeHbaseConnection)

  fakeJsonDumpStorage = exp.DummyObjectWithExpectations()
  fakeJDSModule = exp.DummyObjectWithExpectations()
  fakeJDSModule.expect('JsonDumpStorage', (), jds_kwargs, fakeJsonDumpStorage)

  listOfUuids = ['uuid%03d' % i for i in range(4)]
  listOfUuidJsonPaths = ['/storage/2010/01/16/name/uu/id/uuid%03d.json' % i for i in range(4)]
  listOfUuidJsonContents = [('%d' % i)*10 for i in range(4)]
  listOfUuidDumpPaths = ['/storage/2010/01/16/name/uu/id/uuid%03d.dump' % i for i in range(4)]
  listOfUuidDumpContents = [('%d' % i)*20 for i in range(4)]

  fakeJsonDumpStorage.expect('destructiveDateWalk', (), {}, (x for x in listOfUuids))

  fakeFileOpenFn = exp.DummyObjectWithExpectations()
  for uuid, aJsonFileName, jsonContents, aDumpFileName, dumpContents in zip(listOfUuids,
                                                                            listOfUuidJsonPaths,
                                                                            listOfUuidJsonContents,
                                                                            listOfUuidDumpPaths,
                                                                            listOfUuidDumpContents):
    fakeJsonDumpStorage.expect('getJson', (uuid,), {}, aJsonFileName)
    fakeJsonFile = exp.DummyObjectWithExpectations()
    fakeJsonFile.expect('read', (), {}, jsonContents)
    fakeJsonFile.expect('close', (), {})
    fakeFileOpenFn.expect('__call__', (aJsonFileName,), {}, fakeJsonFile)
    fakeJsonDumpStorage.expect('getDump', (uuid,), {}, aDumpFileName)
    fakeDumpFile = exp.DummyObjectWithExpectations()
    fakeDumpFile.expect('read', (), {}, dumpContents)
    fakeDumpFile.expect('close', (), {})
    fakeFileOpenFn.expect('__call__', (aDumpFileName,), {}, fakeDumpFile)
    fakeHbaseConnection.expect('put_json_dump', (uuid, jsonContents, dumpContents), {})

  for uuid in listOfUuids:
    fakeJsonDumpStorage.expect('remove', (uuid,), {})

  hbr.resubmit(conf, fakeJDSModule, fakeHbaseModule, fakeFileOpenFn)
