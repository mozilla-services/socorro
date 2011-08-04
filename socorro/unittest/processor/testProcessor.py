import socorro.unittest.testlib.expectations as exp
import socorro.lib.util as sutil
import socorro.processor.processor as proc
import socorro.database.database as sdb
import socorro.storage.hbaseClient as hbc
import socorro.storage.crashstorage as cstore
import socorro.lib.datetimeutil as sdt
import socorro.database.schema as sch


import datetime as dt
import threading as thr

sample_meta_json = {"submitted_timestamp": "2011-02-15T00:45:00.000000",
                    "Version": "3.6.6",
                    "StartupTime": "1297831490",
                    "Vendor": "Mozilla",
                    "InstallTime": "1277762202",
                    "BuildID": "20100625231939",
                    "timestamp": 1297831509.6613679,
                    "ProductName": "Firefox",
                    "URL": "http://mozilla.com",
                    "Email": "nobody@mozilla.com",
                    "Throttleable": "1",
                    "SecondsSinceLastCrash": "439",
                    "CrashTime": "1297831492",
                    "EMCheckCompatibility": 'True',
                    "Winsock_LSP": "exciting winsock info",
                    "ReleaseChannel": "release"}

def nothing():
    pass

def createExecutionContext ():
    c = sutil.DotDict()

    config = sutil.DotDict({"databaseHost": "dbhost",
                            "databaseName": "dbname",
                            "databaseUserName": "dbuser",
                            "databasePassword": "dbpass",
                            "processorCheckInTime": dt.timedelta(0,60),
                            "processorCheckInFrequency": dt.timedelta(0,300),
                            "processorLoopTime": dt.timedelta(0,30),
                            "jsonFileSuffix": "json",
                            "dumpFileSuffix": "dump",
                            "processorId": "auto",
                            "numberOfThreads": 4,
                            "batchJobLimit": 1000,
                            "irrelevantSignatureRegEx": ".*",
                            "prefixSignatureRegEx": ".*",
                            "collectAddon": False,
                            "collectCrashProcess": False,
                            "signatureSentinels": [],
                            "signaturesWithLineNumbersRegEx": ".*",
                            "hbaseHost": "hbhost",
                            "hbasePort": "hbport",
                            "hbaseStorageClass": cstore.CrashStorageSystemForHBase,
                            "temporaryFileSystemStoragePath": "/tmp",
                            "elasticSearchOoidSubmissionUrl": "%s",})
    c.config = config

    c.logger = sutil.StringLogger()
    c.config.logger = c.logger

    c.fakeCrashStoragePool = exp.DummyObjectWithExpectations()
    c.fakeCrashStorageModule = exp.DummyObjectWithExpectations()
    c.fakeCrashStorageModule.expect('CrashStoragePool', (config,),
                                    {'storageClass': cstore.CrashStorageSystemForHBase},
                                    c.fakeCrashStoragePool)

    c.fakeConnection = exp.DummyObjectWithExpectations()
    c.fakeCursor = exp.DummyObjectWithExpectations()
    c.fakeDatabaseConnectionPool = exp.DummyObjectWithExpectations()
    c.fakeDatabaseModule = exp.DummyObjectWithExpectations()
    c.fakeDatabaseModule.expect('DatabaseConnectionPool', (config, c.logger),
                                {}, c.fakeDatabaseConnectionPool)

    c.fakeSignalModule = exp.DummyObjectWithExpectations()
    c.fakeSignalModule.expect('signal', (1, proc.Processor.respondToSIGTERM),
                              {},
                              None)
    c.fakeSignalModule.expect('SIGTERM', None, None, 1)
    c.fakeSignalModule.expect('signal', (2, proc.Processor.respondToSIGTERM),
                              {},
                              None)
    c.fakeSignalModule.expect('SIGHUP', None, None, 2)

    c.fakeThreadManager = exp.DummyObjectWithExpectations()
    c.fakeThreadModule = exp.DummyObjectWithExpectations()
    c.fakeThreadModule.expect('TaskManager',
                              (config.numberOfThreads,
                               config.numberOfThreads * 2),
                              {},
                              c.fakeThreadManager)
    c.fakeNowFunc = exp.DummyObjectWithExpectations()
    return c

def getMockedProcessorAndContext():
    c = createExecutionContext()
    class MockedProcessor(proc.Processor):
        def registration (self):
            self.processorId = 288
            self.priorityJobsTableName = 'fred'

    p = MockedProcessor(c.config,
                        sdb=c.fakeDatabaseModule,
                        cstore=c.fakeCrashStorageModule,
                        signal=c.fakeSignalModule,
                        sthr=c.fakeThreadModule,
                        nowFunc=c.fakeNowFunc,
                       )
    return p, c

def testConstructor():
    """testConstructor: just setting up the environment"""
    p, c = getMockedProcessorAndContext()
    assert p.processorId == 288
    assert p.priorityJobsTableName == 'fred'
    assert p.sdb == c.fakeDatabaseModule
    assert p.databaseConnectionPool == c.fakeDatabaseConnectionPool
    assert p.processorLoopTime == 30
    assert p.config == c.config
    assert p.quit == False

def testRegistration_1():
    """testRegistration_1: No dead processor"""
    c = createExecutionContext()

    c.fakeOsModule = exp.DummyObjectWithExpectations()

    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', (), {},
                                        (c.fakeConnection, c.fakeCursor))
    c.fakeOsModule.expect('uname', (), {}, [ None, 'testHost'])
    c.fakeOsModule.expect('getpid', (), {}, 666)
    c.fakeDatabaseModule.expect('singleValueSql',
                                (c.fakeCursor,
                                 "select now() - interval '0:01:00'",),
                                {},
                                '2011-02-15 00:00:00'
                               )

    c.fakeDatabaseModule.expect('singleValueSql',
                                (c.fakeCursor,
                                 "select id from processors"
                                 " where lastseendatetime <"
                                 " '2011-02-15 00:00:00' limit 1",),
                                {},
                                None,
                                sdb.SQLDidNotReturnSingleValue()
                               )
    c.fakeCursor.expect('execute',
                        ("insert into processors (name, startdatetime, "
                         "lastseendatetime) values (%s, now(), now())",
                         ('testHost_666',)),
                        {},
                        None)
    c.fakeDatabaseModule.expect('singleValueSql',
                                (c.fakeCursor,
                                 "select id from processors"
                                 " where name = 'testHost_666'",),
                                {},
                                99,
                               )
    c.fakeCursor.expect('execute',
                        ("update processors set name = %s, "
                         "startdatetime = now(), lastseendatetime = now()"
                         " where id = %s",
                         ('testHost_666', 99)),
                        {},
                        None)
    c.fakeCursor.expect('execute',
                        ("update jobs set"
                         "    starteddatetime = NULL,"
                         "    completeddatetime = NULL,"
                         "    success = NULL "
                         "where"
                         "    owner = %s", (99, )),
                        {},
                        None)
    c.fakeCursor.expect('execute',
                        ("create table priority_jobs_99 (uuid varchar(50) not null "
                         "primary key)",),
                        {},
                        None)
    c.fakeConnection.expect('commit', (), {})

    p = proc.Processor(c.config,
                       sdb=c.fakeDatabaseModule,
                       cstore=c.fakeCrashStorageModule,
                       signal=c.fakeSignalModule,
                       sthr=c.fakeThreadModule,
                       os=c.fakeOsModule,
                      )

def testRegistration_2():
    """testRegistration_2: dead processor found"""
    c = createExecutionContext()

    c.fakeOsModule = exp.DummyObjectWithExpectations()

    c.fakeConnection = exp.DummyObjectWithExpectations()
    c.fakeCursor = exp.DummyObjectWithExpectations()
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', (), {},
                                        (c.fakeConnection, c.fakeCursor))
    c.fakeOsModule.expect('uname', (), {}, [ None, 'testHost'])
    c.fakeOsModule.expect('getpid', (), {}, 666)
    c.fakeDatabaseModule.expect('singleValueSql',
                                (c.fakeCursor,
                                 "select now() - interval '0:01:00'",),
                                {},
                                '2011-02-15 00:00:00'
                               )

    c.fakeDatabaseModule.expect('singleValueSql',
                                (c.fakeCursor,
                                 "select id from processors"
                                 " where lastseendatetime <"
                                 " '2011-02-15 00:00:00' limit 1",),
                                {},
                                99
                               )
    c.fakeCursor.expect('execute',
                        ("update processors set name = %s, "
                         "startdatetime = now(), lastseendatetime = now()"
                         " where id = %s",
                         ('testHost_666', 99)),
                        {},
                        None)
    c.fakeCursor.expect('execute',
                        ("update jobs set"
                         "    starteddatetime = NULL,"
                         "    completeddatetime = NULL,"
                         "    success = NULL "
                         "where"
                         "    owner = %s", (99, )),
                        {},
                        None)
    c.fakeCursor.expect('execute',
                        ("create table priority_jobs_99 (uuid varchar(50) not null "
                         "primary key)",),
                        {},
                        None)
    c.fakeConnection.expect('commit', (), {})

    p = proc.Processor(c.config,
                       sdb=c.fakeDatabaseModule,
                       cstore=c.fakeCrashStorageModule,
                       signal=c.fakeSignalModule,
                       sthr=c.fakeThreadModule,
                       os=c.fakeOsModule,
                      )

def testQuitCheck():
    """testQuitCheck: to quit or not to quit"""
    p, c = getMockedProcessorAndContext()
    try:
        p.quitCheck()
    except KeyboardInterrupt:
        assert False, "KeyboardInterrupt should not have been raised"
    p.quit = True
    try:
        p.quitCheck()
        assert False, "KeyboardInterrupt should have been raised"
    except KeyboardInterrupt:
        pass

def testCheckin1():
    """testCheckin1: update registration"""
    p, c = getMockedProcessorAndContext()
    c.fakeNowFunc.expect('__call__', (), {}, dt.datetime(2011, 2, 15))
    c.fakeNowFunc.expect('__call__', (), {}, dt.datetime(2011, 2, 15))
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', (), {},
                                        (c.fakeConnection, c.fakeCursor))
    c.fakeCursor.expect('execute',
                        ("update processors set lastseendatetime = %s "
                         "where id = %s",
                         (dt.datetime(2011, 2, 15), 288)),
                        {},
                        None)
    c.fakeConnection.expect('commit', (), {})
    c.fakeNowFunc.expect('__call__', (), {}, dt.datetime(2011, 2, 15))
    p.checkin()
    assert p.lastCheckInTimestamp == dt.datetime(2011, 2, 15)

def testCheckin2():
    """testCheckin2: check in off schedule"""
    p, c = getMockedProcessorAndContext()
    c.fakeNowFunc.expect('__call__', (), {}, dt.datetime(1950, 1, 1))
    p.checkin()

def testCleanup():
    """testCleanup: orderly shutdown"""
    p, c = getMockedProcessorAndContext()
    c.fakeThreadManager.expect('waitForCompletion', (), {}, None)
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', (), {},
                                        (c.fakeConnection, c.fakeCursor))
    c.fakeCursor.expect('execute',
                        ("update processors set lastseendatetime = '1999-01-01'"
                         " where id = %s", (288,)),
                        {},
                        None)
    c.fakeConnection.expect('commit', (), {})
    c.fakeCursor.expect('execute',
                        ("drop table fred",),
                        {},
                        None)
    c.fakeConnection.expect('commit', (), {})
    c.fakeDatabaseConnectionPool.expect('cleanup', (), {})
    c.fakeCrashStoragePool.expect('cleanup', (), {})

def testSubmitJobToThreads():
    """testSubmitJobToThreads: accept a new job"""
    p, c = getMockedProcessorAndContext()
    fakeJobTuple = ('a Job', 'stuff', 'other')
    c.fakeNowFunc.expect('__call__', (), {}, dt.datetime(2011, 2, 15))
    c.fakeDatabaseModule.expect('transaction_execute_with_retry',
                                (c.fakeDatabaseConnectionPool,
                                 "update jobs set starteddatetime = %s where "
                                 "id = %s",
                                 (dt.datetime(2011, 2, 15), fakeJobTuple[0])),
                                 {})
    c.fakeThreadManager.expect('newTask',
                               (p.processJobWithRetry, fakeJobTuple),
                               {})
    p.submitJobToThreads(fakeJobTuple)

def priorityQuery(c, returnValues):
    c.fakeDatabaseModule.expect('transaction_execute_with_retry',
                                (c.fakeDatabaseConnectionPool,
                                 "select"
                                 "    j.id,"
                                 "    pj.uuid,"
                                 "    1,"
                                 "    j.starteddatetime "
                                 "from"
                                 "    jobs j right join fred pj on j.uuid = "
                                 "pj.uuid",),
                                 {},
                                 returnValues)

def testNewPriorityJobsIter1():
    """testNewPriorityJobsIter1: no priority jobs"""
    p, c = getMockedProcessorAndContext()
    for x in range(4):
        priorityQuery(c, [])
    i = p.newPriorityJobsIter()
    for x in range(4):
        assert i.next() is None

def testNewPriorityJobsIter2():
    """testNewPriorityJobsIter1: two priority jobs, one already started"""
    p, c = getMockedProcessorAndContext()
    priorityJobsList1 = [(15,'ooid1',1,None),
                         (16,'ooid2',1,dt.datetime(2011,1,1)) ]
    priorityQuery(c, priorityJobsList1)
    c.fakeDatabaseModule.expect('transaction_execute_with_retry',
                                (c.fakeDatabaseConnectionPool,
                                 "delete from fred where uuid = %s",
                                 ('ooid2',)),
                                 {})
    c.fakeDatabaseModule.expect('transaction_execute_with_retry',
                                (c.fakeDatabaseConnectionPool,
                                 "delete from fred where uuid = %s",
                                 ('ooid1',)),
                                 {})
    priorityQuery(c, [])
    i = p.newPriorityJobsIter()
    r = i.next()
    e = (15, 'ooid1', 1)
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)
    r = i.next()
    e = None
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)
    assert 'ooid1' in p.priority_job_set, "expected 'ooid1' to be in " \
                                          "priority_job_set, but it wasn't"
    assert 'ooid2' not in p.priority_job_set, "expected 'ooid2' to NOT be in " \
                                          "priority_job_set, but it was"

def normalQuery(c, returnValues):
    c.fakeDatabaseModule.expect('transaction_execute_with_retry',
                                (c.fakeDatabaseConnectionPool,
                                 "select"  \
                                 "    j.id,"  \
                                 "    j.uuid,"  \
                                 "    priority "  \
                                 "from"  \
                                 "    jobs j "  \
                                 "where"  \
                                 "    j.owner = 288"  \
                                 "    and j.starteddatetime is null "  \
                                 "order by queueddatetime"  \
                                 "  limit 1000",),
                                 {},
                                 returnValues)

def testNewNormalJobsIter1():
    """testNewNormalJobsIter1: nothing to do"""
    p, c = getMockedProcessorAndContext()
    for x in range(4):
        normalQuery(c, [])
    i = p.newNormalJobsIter()
    for x in range(4):
        assert i.next() is None

def testNewNormalJobsIter2():
    """testNewNormalJobsIter2: two jobs"""
    p, c = getMockedProcessorAndContext()
    normalJobsList1 = [(15,'ooid1',1),
                       (16,'ooid2',1) ]
    normalQuery(c, normalJobsList1)
    normalQuery(c, [])
    i = p.newNormalJobsIter()
    r = i.next()
    e = (16,'ooid2',1)
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)
    r = i.next()
    e = (15, 'ooid1', 1)
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)
    normalQuery(c, [])
    r = i.next()
    e = None
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)
    normalQuery(c, [])
    r = i.next()
    e = None
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testIncomingJobStream():
    """testIncomingJobStream: combining priority and normal iterators"""
    p, c = getMockedProcessorAndContext()
    p.newPriorityJobsIter = [None, None, None, None, None, None, None,
                             ('P','P'),
                             None, None, None, None].__iter__
    p.newNormalJobsIter = [(1,1), (2,2), (3,3), None, (4,4), (5,5), (6,6),
                           (7,7), None, (8,8)].__iter__
    results = [(1,1), (2,2), (3,3), (4,4), (5,5), (6,6), ('P','P'), (7,7),
               (8,8)]
    p.responsiveSleep = lambda i: None
    def nothing(): pass
    p.checkin = nothing
    i = p.incomingJobStream()
    for e in results:
        r = i.next()
        assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testStart():
    """testStart: mainthread"""
    p, c = getMockedProcessorAndContext()
    p.incomingJobStream = [(1,1), (2,2), (3,3), (4,4), (5,5), (6,6), ('P','P'),
                           (7,7), (8,8)].__iter__
    resultIter = p.incomingJobStream()
    def testSubmit (r):
        try:
            e = resultIter.next()
            assert e == r, 'expected\n%s\nbut got\n%s' % (e, r)
        except StopIteration:
            raise KeyboardInterrupt
    p.submitJobToThreads = testSubmit
    p.cleanup = nothing
    p.start()
    assert p.quit == True

def testConvertDatesInDictToString():
    """testConvertDatesInDictToString: for jsonification"""
    d = { 'a': 1,
          'b': 2,
          'c': 3,
          'd': dt.datetime(2011, 2, 15, 11, 31, 22),
          'e': 5,
          'f': dt.datetime(2011, 2, 15, 11, 31, 22),
        }
    proc.Processor.convertDatesInDictToString(d)
    assert d['a'] == 1
    assert d['b'] == 2
    assert d['c'] == 3
    e = '2011-02-15 11:31:22.0'
    r = d['d']
    assert e == r, "expected\n'%s'\nbut got\n'%s'" % (e, r)
    assert d['e'] == 5
    assert d['f'] == '2011-02-15 11:31:22.0'

def testSanitizeDict():
    """testSanitizeDict: no secret data gets out"""
    d = { 'a': 1,
          'c': 3,
          'e': 5,
          'g': 7
        }
    de = d.copy()
    d['url'] = 2
    d['email'] = 4
    d['user_id'] = 6
    proc.Processor.sanitizeDict(d)
    assert de == d, "expected\n'%s'\nbut got\n'%s'" % (de, d)

def testSaveProcessedDumpJson():
    """testSaveProcessedDumpJson: commit back to hbase"""
    p, c = getMockedProcessorAndContext()
    d = { 'a': 1,
          'c': 3,
          'd': dt.datetime(2011, 2, 15, 11, 31, 22),
          'e': 5,
          'f': dt.datetime(2011, 2, 15, 11, 31, 22),
          'g': 7,
          'uuid': 'uuid1'
        }
    de = d.copy()
    de['d'] = '2011-02-15 11:31:22.0'
    de['f'] = '2011-02-15 11:31:22.0'
    d['url'] = 2
    d['email'] = 4
    d['user_id'] = 6
    fakeThreadLocalCrashStorage = exp.DummyObjectWithExpectations()
    fakeThreadLocalCrashStorage.expect('save_processed', ('uuid1', de), {})
    p.saveProcessedDumpJson(d, fakeThreadLocalCrashStorage)

def testBackoffSecondsGenerator():
    """testBackoffSecondsGenerator: time increment iterator"""
    e = [10, 30, 60, 120, 300, 300, 300, 300]
    r = []
    i = proc.Processor.backoffSecondsGenerator()
    for x in range(len(e)):
        r.append(i.next())
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testProcessJobWithRetry1():
    """testProcessJobWithRetry1: repeated failures of hbase until it works"""
    p, c = getMockedProcessorAndContext()
    fakeJobTuple = (1, 2, 3)
    fakeProcessJob = exp.DummyObjectWithExpectations()
    fakeResponsiveSleep = exp.DummyObjectWithExpectations()
    fakeProcessJob.expect('__call__', (fakeJobTuple,), {},
                          proc.Processor.criticalError)
    fakeResponsiveSleep.expect('__call__',
                (10, 10, "waiting for retry after failure in crash storage"),
                {})
    fakeProcessJob.expect('__call__', (fakeJobTuple,), {},
                          proc.Processor.criticalError)
    fakeResponsiveSleep.expect('__call__',
                (30, 10, "waiting for retry after failure in crash storage"),
                {})
    fakeProcessJob.expect('__call__', (fakeJobTuple,), {},
                          proc.Processor.criticalError)
    fakeResponsiveSleep.expect('__call__',
                (60, 10, "waiting for retry after failure in crash storage"),
                {})
    fakeProcessJob.expect('__call__', (fakeJobTuple,), {},
                          proc.Processor.criticalError)
    fakeResponsiveSleep.expect('__call__',
                (120, 10, "waiting for retry after failure in crash storage"),
                {})
    fakeProcessJob.expect('__call__', (fakeJobTuple,), {},
                          proc.Processor.criticalError)
    fakeResponsiveSleep.expect('__call__',
                (300, 10, "waiting for retry after failure in crash storage"),
                {})
    fakeProcessJob.expect('__call__', (fakeJobTuple,), {},
                          proc.Processor.criticalError)
    fakeResponsiveSleep.expect('__call__',
                (300, 10, "waiting for retry after failure in crash storage"),
                {})
    fakeProcessJob.expect('__call__', (fakeJobTuple,), {},
                          proc.Processor.ok)
    p.processJobWithRetry(fakeJobTuple)

def testProcessJobWithRetry2():
    """testProcessJobWithRetry2: shorter failures until it works"""
    p, c = getMockedProcessorAndContext()
    fakeJobTuple = (1, 2, 3)
    fakeProcessJob = exp.DummyObjectWithExpectations()
    fakeResponsiveSleep = exp.DummyObjectWithExpectations()
    fakeProcessJob.expect('__call__', (fakeJobTuple,), {},
                          proc.Processor.criticalError)
    fakeResponsiveSleep.expect('__call__',
                (10, 10, "waiting for retry after failure in crash storage"),
                {})
    fakeProcessJob.expect('__call__', (fakeJobTuple,), {},
                          proc.Processor.criticalError)
    fakeResponsiveSleep.expect('__call__',
                (30, 10, "waiting for retry after failure in crash storage"),
                {})
    fakeProcessJob.expect('__call__', (fakeJobTuple,), {},
                          proc.Processor.quit)

def testProcessJob01():
    """testProcessJob01: immeditate quit"""
    p, c = getMockedProcessorAndContext()
    p.quit = True
    r = p.processJob('anything')
    e = proc.Processor.quit
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testProcessJob02():
    """testProcessJob02: return on bad database"""
    p, c = getMockedProcessorAndContext()
    fakeJobTuple = (123, 'uuid1', 1)
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', (), {},
                                        None,
                                        sdb.db_module.OperationalError())

    r = p.processJob(fakeJobTuple)
    e = proc.Processor.criticalError
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testProcessJob03():
    """testProcessJob03: return on bad hbase"""
    threadName = thr.currentThread().getName()
    p, c = getMockedProcessorAndContext()
    fakeJobTuple = (123, 'uuid1', 1)
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', (), {},
                                        (c.fakeConnection, c.fakeCursor))
    c.fakeCrashStorage = exp.DummyObjectWithExpectations()
    c.fakeCrashStoragePool.expect('crashStorage', (threadName,), {},
                                  None,
                                  hbc.FatalException(Exception()))
    r = p.processJob(fakeJobTuple)
    e = proc.Processor.criticalError
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testProcessJob04():
    """testProcessJob04: other initial fatal condition"""
    threadName = thr.currentThread().getName()
    p, c = getMockedProcessorAndContext()
    fakeJobTuple = (123, 'uuid1', 1)
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', (), {},
                                        (c.fakeConnection, c.fakeCursor))
    c.fakeCrashStorage = exp.DummyObjectWithExpectations()
    c.fakeCrashStoragePool.expect('crashStorage', (threadName,), {},
                                  None,
                                  Exception())
    r = p.processJob(fakeJobTuple)
    e = proc.Processor.quit
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testProcessJob05():
    """testProcessJob05: unexpected commit exception"""
    threadName = thr.currentThread().getName()
    p, c = getMockedProcessorAndContext()
    ooid1 = 'ooid1'
    fakeJobTuple = (123, ooid1, 1)
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', (), {},
                                        (c.fakeConnection, c.fakeCursor))
    c.fakeCrashStorage = exp.DummyObjectWithExpectations()
    c.fakeCrashStoragePool.expect('crashStorage', (threadName,), {},
                                  c.fakeCrashStorage)
    startedDatetime = dt.datetime(2011, 2, 15, 1, 0, 0)
    c.fakeNowFunc.expect('__call__', (), {}, startedDatetime)
    c.fakeCursor.expect('execute',
                        ('update jobs set starteddatetime = %s where id = %s',
                         (startedDatetime, 123)), {})
    c.fakeConnection.expect('commit', (), {}, None)
    c.fakeCrashStorage.expect('get_meta', (ooid1,), {},
                              sample_meta_json)
    date_processed =  \
        sdt.datetimeFromISOdateString(sample_meta_json["submitted_timestamp"])
    fakeInsertReportIntoDatabaseFn = exp.DummyObjectWithExpectations()
    new_report_record = {
                        }
    fakeInsertReportIntoDatabaseFn.expect('__call__',
                                          (c.fakeCursor,
                                           ooid1,
                                           sample_meta_json,
                                           date_processed, []),
                                          {},
                                          new_report_record)
    p.insertReportIntoDatabase = fakeInsertReportIntoDatabaseFn
    c.fakeConnection.expect('commit', (), {}, None,
                            sdb.db_module.OperationalError())

    r = p.processJob(fakeJobTuple)
    e = proc.Processor.criticalError
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testProcessJob06():
    """testProcessJob06: unexpected breakpad mdsw exception"""
    threadName = thr.currentThread().getName()
    p, c = getMockedProcessorAndContext()
    ooid1 = 'ooid1'
    jobId = 123
    fakeJobTuple = (jobId, ooid1, 1)
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', (), {},
                                        (c.fakeConnection, c.fakeCursor))
    c.fakeCrashStorage = exp.DummyObjectWithExpectations()
    c.fakeCrashStoragePool.expect('crashStorage', (threadName,), {},
                                  c.fakeCrashStorage)
    startedDatetime = dt.datetime(2011, 2, 15, 1, 0, 0)
    c.fakeNowFunc.expect('__call__', (), {}, startedDatetime)
    c.fakeCursor.expect('execute',
                        ('update jobs set starteddatetime = %s where id = %s',
                         (startedDatetime, jobId)), {})
    c.fakeConnection.expect('commit', (), {}, None)
    c.fakeCrashStorage.expect('get_meta', (ooid1,), {},
                              sample_meta_json)
    date_processed =  \
        sdt.datetimeFromISOdateString(sample_meta_json["submitted_timestamp"])
    fakeInsertReportIntoDatabaseFn = exp.DummyObjectWithExpectations()
    reportId = 345
    proc_err_msg_list = []
    new_report_record = { 'id': reportId,
                        }
    fakeInsertReportIntoDatabaseFn.expect('__call__',
                                          (c.fakeCursor,
                                           ooid1,
                                           sample_meta_json,
                                           date_processed,
                                           proc_err_msg_list),
                                          {},
                                          new_report_record)
    p.insertReportIntoDatabase = fakeInsertReportIntoDatabaseFn
    c.fakeConnection.expect('commit', (), {}, None)
    dump_pathname = '/tmp/uuid1.dump'
    c.fakeCrashStorage.expect('dumpPathForUuid',
                              (ooid1, c.config.temporaryFileSystemStoragePath),
                              {},
                              dump_pathname)
    fakeDoBreakpadStackDumpAnalysisFn = exp.DummyObjectWithExpectations()
    p.doBreakpadStackDumpAnalysis = fakeDoBreakpadStackDumpAnalysisFn
    additional_report_values = { #'hangid': 'hang00001',
                                 'signature': 's'*255,
                               }
    fakeDoBreakpadStackDumpAnalysisFn.expect('__call__',
                                             (reportId,
                                              ooid1,
                                              dump_pathname,
                                              False,
                                              c.fakeCursor,
                                              date_processed,
                                              proc_err_msg_list),
                                             {},
                                             None,
                                             Exception())
    c.fakeCrashStorage.expect('cleanUpTempDumpStorage',
                              (ooid1, c.config.temporaryFileSystemStoragePath),
                              {})

    c.fakeConnection.expect('rollback', (), {}, None)
    failedDatetime = dt.datetime(2011,2,15,1,1,0)
    c.fakeNowFunc.expect('__call__', (), {}, failedDatetime)
    c.fakeNowFunc.expect('__call__', (), {}, failedDatetime)
    c.fakeNowFunc.expect('__call__', (), {}, failedDatetime)
    message = '; '.join(proc_err_msg_list).replace("'", "''")
    c.fakeCursor.expect('execute',
                        ("update jobs set completeddatetime = %s, success = "
                         "False, message = %s where id = %s",
                         (failedDatetime, message, jobId)),
                        {})
    c.fakeConnection.expect('commit', (), {}, None)
    c.fakeCursor.expect('execute',
                        ("update reports set started_datetime = timestamp "
                         "without time zone %s, completed_datetime = "
                         "timestamp without time zone %s, success = False, "
                         "processor_notes = %s where id = %s and "
                         "date_processed = timestamp without time zone %s",
                         (startedDatetime, failedDatetime, message, reportId,
                          date_processed)),
                        {})
    c.fakeConnection.expect('commit', (), {}, None)
    fakeSaveProcessedDumpJson = exp.DummyObjectWithExpectations()
    fakeSaveProcessedDumpJson.expect('__call__',
                                     (new_report_record, c.fakeCrashStorage),
                                     {})
    p.saveProcessedDumpJson = fakeSaveProcessedDumpJson

    r = p.processJob(fakeJobTuple)
    e = proc.Processor.ok
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testProcessJob07():
    """testProcessJob07: success"""
    threadName = thr.currentThread().getName()
    p, c = getMockedProcessorAndContext()
    p.submitOoidToElasticSearch = lambda x: None   # eliminate this call
    ooid1 = 'ooid1'
    jobId = 123
    fakeJobTuple = (jobId, ooid1, 1)
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', (), {},
                                        (c.fakeConnection, c.fakeCursor))
    c.fakeCrashStorage = exp.DummyObjectWithExpectations()
    c.fakeCrashStoragePool.expect('crashStorage', (threadName,), {},
                                  c.fakeCrashStorage)
    startedDatetime = dt.datetime(2011, 2, 15, 1, 0, 0)
    c.fakeNowFunc.expect('__call__', (), {}, startedDatetime)
    c.fakeCursor.expect('execute',
                        ('update jobs set starteddatetime = %s where id = %s',
                         (startedDatetime, jobId)), {})
    c.fakeConnection.expect('commit', (), {}, None)
    c.fakeCrashStorage.expect('get_meta', (ooid1,), {},
                              sample_meta_json)
    date_processed =  \
        sdt.datetimeFromISOdateString(sample_meta_json["submitted_timestamp"])
    fakeInsertReportIntoDatabaseFn = exp.DummyObjectWithExpectations()
    reportId = 345
    #proc_err_msg_list = ['a', 'b']
    proc_err_msg_list = []
    new_report_record = { 'id': reportId,
                          'hangid': 'hang00001',
                        }
    fakeInsertReportIntoDatabaseFn.expect('__call__',
                                          (c.fakeCursor,
                                           ooid1,
                                           sample_meta_json,
                                           date_processed,
                                           proc_err_msg_list),
                                          {},
                                          new_report_record)
    p.insertReportIntoDatabase = fakeInsertReportIntoDatabaseFn
    c.fakeConnection.expect('commit', (), {}, None)
    dump_pathname = '/tmp/uuid1.dump'
    c.fakeCrashStorage.expect('dumpPathForUuid',
                              (ooid1, c.config.temporaryFileSystemStoragePath),
                              {},
                              dump_pathname)
    fakeDoBreakpadStackDumpAnalysisFn = exp.DummyObjectWithExpectations()
    p.doBreakpadStackDumpAnalysis = fakeDoBreakpadStackDumpAnalysisFn
    expected_signature = 'hang | %s...' % ('s' * 245)
    additional_report_values = {'signature': 'hang | %s...' % ('s' * 245),
                                'success': True,
                                'flash_version': "all.bad",
                                'truncated': False,
                                'topmost_filenames': [ 'myfile.cpp' ],
                                #'expected_topmost': 'myfile.cpp',
                                #'expected_addons_checked': True,
                               }
    fakeDoBreakpadStackDumpAnalysisFn.expect('__call__',
                                             (reportId,
                                              ooid1,
                                              dump_pathname,
                                              True,
                                              c.fakeCursor,
                                              date_processed,
                                              proc_err_msg_list),
                                             {},
                                             additional_report_values)
    c.fakeCrashStorage.expect('cleanUpTempDumpStorage',
                              (ooid1, c.config.temporaryFileSystemStoragePath),
                              {})

    completedDateTime = dt.datetime(2011,2,15,1,1,0)
    c.fakeNowFunc.expect('__call__', (), {}, completedDateTime)
    c.fakeCursor.expect('execute',
                        ("update jobs set completeddatetime = %s, success = %s "
                         "where id = %s",
                         (completedDateTime,
                          additional_report_values['success'],
                          jobId)),
                        {})
    reportsSql = """
      update reports set
        signature = %%s,
        processor_notes = %%s,
        started_datetime = timestamp without time zone %%s,
        completed_datetime = timestamp without time zone %%s,
        success = %%s,
        truncated = %%s,
        topmost_filenames = %%s,
        addons_checked = %%s,
        flash_version = %%s
      where id = %s and date_processed = timestamp without time zone '%s'
      """ % (reportId, date_processed)
    c.fakeCursor.expect('execute',
                        (reportsSql,
                         (expected_signature,
                          '; '.join(proc_err_msg_list),
                          startedDatetime,
                          completedDateTime,
                          additional_report_values['success'],
                          additional_report_values['truncated'],
                          #additional_report_values['expected_topmost'],
                          'myfile.cpp',
                          #additional_report_values['expected_addons_checked'],
                          True,
                          additional_report_values['flash_version'],
                          )),
                        {})
    c.fakeConnection.expect('commit', (), {}, None)
    fakeSaveProcessedDumpJson = exp.DummyObjectWithExpectations()
    nrr = {'Winsock_LSP': 'exciting winsock info',
           'flash_version': 'all.bad',
           'success': True,
           'dump': '',
           'startedDateTime': dt.datetime(2011, 2, 15, 1, 0),
           'truncated': False,
           'signature': 'hang | ssssssssssssssssssssssssssssssssssssssssssssss'
                        'sssssssssssssssssssssssssssssssssssssssssssssssssssss'
                        'sssssssssssssssssssssssssssssssssssssssssssssssssssss'
                        'sssssssssssssssssssssssssssssssssssssssssssssssssssss'
                        'ssssssssssssssssssssssssssssssssssssssss...',
            'hangid': 'hang00001',
            'processor_notes': '',
            'topmost_filenames': ['myfile.cpp'],
            'id': 345,
            'completeddatetime': dt.datetime(2011, 2, 15, 1, 1),
            'ReleaseChannel': 'release',
           }
    fakeSaveProcessedDumpJson.expect('__call__',
                                     (nrr, c.fakeCrashStorage),
                                     #(new_report_record, c.fakeCrashStorage),
                                     #({}, c.fakeCrashStorage),
                                     {})
    p.saveProcessedDumpJson = fakeSaveProcessedDumpJson
    r = p.processJob(fakeJobTuple)
    e = proc.Processor.ok
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testGetJsonOrWarn():
    """testGetJsonOrWarn: several invocations"""
    message_list = []
    d = { 'key': 'value' }
    r = proc.Processor.getJsonOrWarn(d, 'key', message_list)
    assert r == 'value'
    assert message_list == []

    r = proc.Processor.getJsonOrWarn(d, 'non-key', message_list)
    assert r == None
    assert 'WARNING: JSON file missing non-key' in message_list

    message_list = []
    d = { 'key': 'v'*100 }
    r = proc.Processor.getJsonOrWarn(d, 'key', message_list, maxLength=10)
    assert r == 'v'*10
    assert message_list == []

    message_list = []
    d = { 'key': 23 }
    r = proc.Processor.getJsonOrWarn(d, 'key', message_list)
    assert r == None
    assert len(message_list) == 1
    print message_list
    assert "'int'" in message_list[0]
    assert "subscriptable" in message_list[0]

expected_report_tuple = ('ooid1',
                         dt.datetime(2011, 2, 16, 4, 44, 52,
                                     tzinfo=proc.Processor.utctz),
                         dt.datetime(2011, 2, 15, 1, 0),
                         'Firefox',
                         '3.6.6',
                         '20100625231939',
                         'http://mozilla.com',
                         20069290,
                         439,
                         2,
                         'nobody@mozilla.com',
                         dt.datetime(2010, 6, 25, 23, 0),
                         '',
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         'release')

expected_report_dict =  {'client_crash_date':
                                       dt.datetime(2011, 2, 16, 4, 44, 52,
                                                   tzinfo=proc.Processor.utctz),
                         'product': 'Firefox',
                         'install_age': 20069290,
                         'distributor': None,
                         'topmost_filenames': None,
                         'id': 234,
                         'user_comments': None,
                         'build_date': dt.datetime(2010, 6, 25, 23, 0),
                         'uptime': 2,
                         'user_id': '',
                         'uuid': 'ooid1',
                         'flash_version': None,
                         'distributor_version': None,
                         'process_type': None,
                         'hangid': None,
                         'version': '3.6.6',
                         'build': '20100625231939',
                         'email': 'nobody@mozilla.com',
                         'addons_checked': None,
                         'app_notes': None,
                         'last_crash': 439,
                         'date_processed': dt.datetime(2011, 2, 15, 1, 0),
                         'url': 'http://mozilla.com',
                         'release_channel': 'release'}

def testInsertReportIntoDatabase01():
    """testInsertReportIntoDatabase01: success"""
    p, c = getMockedProcessorAndContext()
    ooid1 = 'ooid1'
    date_processed = dt.datetime(2011,2,15,1,0,0)
    json_doc = sample_meta_json
    error_list = []
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', None, None,
                                        17)
    fakeReportsTable = exp.DummyObjectWithExpectations()
    fakeReportsTable.expect('columns',
                            None,
                            None,
                            sch.ReportsTable(logger=c.logger).columns)
    fakeReportsTable.expect('insert',
                            (c.fakeCursor,
                             expected_report_tuple,
                             17,),
                            { 'date_processed': date_processed })
    p.reportsTable = fakeReportsTable
    c.fakeDatabaseModule.expect('singleValueSql',
                                (c.fakeCursor,
                                 "select id from reports where uuid = "
                                 "'ooid1' and date_processed = timestamp "
                                 "without time zone '2011-02-15 01:00:00'"),
                                {},
                                234)

    r = p.insertReportIntoDatabase(c.fakeCursor,
                                   ooid1,
                                   json_doc,
                                   date_processed,
                                   error_list)
    e = expected_report_dict
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testInsertAdddonsIntoDatabase1():
    """testInsertAdddonsIntoDatabase1: no addons"""
    p, c = getMockedProcessorAndContext()
    reportId = 123
    date_processed = dt.datetime(2011,2,15,1,0,0)
    error_list = []
    r = p.insertAdddonsIntoDatabase(c.fakeCursor,
                                    reportId,
                                    sample_meta_json,
                                    date_processed,
                                    error_list)
    e = []
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testInsertAdddonsIntoDatabase2():
    """testInsertAdddonsIntoDatabase2: 5 addons"""
    p, c = getMockedProcessorAndContext()
    reportId = 123
    jd = sample_meta_json.copy()
    jd['Add-ons'] = "{3f963a5b-e555-4543-90e2-c3908898db71}:" \
                    "8.5,jqs@sun.com:1.0,{20a82645-c095-46ed-80e3-08825" \
                    "760534b}:1.1,avg@igeared:2.507.024.001,{972ce4c6-7" \
                    "e08-4474-a285-3208198ce6fd}:3.5.3"
    date_processed = dt.datetime(2011,2,15,1,0,0)
    error_list = []
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', None, None,
                                        17)
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', None, None,
                                        17)
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', None, None,
                                        17)
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', None, None,
                                        17)
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', None, None,
                                        17)
    fakeExtensionsTable = exp.DummyObjectWithExpectations()
    fakeExtensionsTable.expect('insert',
                               (c.fakeCursor,
                                (reportId,
                                 date_processed,
                                 0,
                                 "{3f963a5b-e555-4543-90e2-c3908898db71}",
                                 "8.5"),
                                17),
                               {'date_processed':date_processed})
    fakeExtensionsTable.expect('insert',
                               (c.fakeCursor,
                                (reportId,
                                 date_processed,
                                 1,
                                 "jqs@sun.com",
                                 "1.0"),
                                17),
                               {'date_processed':date_processed})
    fakeExtensionsTable.expect('insert',
                               (c.fakeCursor,
                                (reportId,
                                 date_processed,
                                 2,
                                 "{20a82645-c095-46ed-80e3-08825760534b}",
                                 "1.1"),
                                17),
                               {'date_processed':date_processed})
    fakeExtensionsTable.expect('insert',
                               (c.fakeCursor,
                                (reportId,
                                 date_processed,
                                 3,
                                 "avg@igeared",
                                 "2.507.024.001"),
                                17),
                               {'date_processed':date_processed})
    fakeExtensionsTable.expect('insert',
                               (c.fakeCursor,
                                (reportId,
                                 date_processed,
                                 4,
                                 "{972ce4c6-7e08-4474-a285-3208198ce6fd}",
                                 "3.5.3"),
                                17),
                               {'date_processed':date_processed})
    p.extensionsTable = fakeExtensionsTable
    r = p.insertAdddonsIntoDatabase(c.fakeCursor,
                                    reportId,
                                    jd,
                                    date_processed,
                                    error_list)
    e = [["{3f963a5b-e555-4543-90e2-c3908898db71}", "8.5"],
         ["jqs@sun.com", "1.0"],
         ["{20a82645-c095-46ed-80e3-08825760534b}", "1.1"],
         ["avg@igeared", "2.507.024.001"],
         ["{972ce4c6-7e08-4474-a285-3208198ce6fd}", "3.5.3"]
        ]
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testInsertAdddonsIntoDatabase3():
    """testInsertAdddonsIntoDatabase3: 1 bad addon in 3"""
    p, c = getMockedProcessorAndContext()
    reportId = 123
    jd = sample_meta_json.copy()
    jd['Add-ons'] = "jqs@sun.com:1.0,this_addon_is_missing_its_version," \
                    "avg@igeared:2.507.024.001"
    date_processed = dt.datetime(2011,2,15,1,0,0)
    error_list = []
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', None, None,
                                        17)
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', None, None,
                                        17)
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair', None, None,
                                        17)
    fakeExtensionsTable = exp.DummyObjectWithExpectations()
    fakeExtensionsTable.expect('insert',
                               (c.fakeCursor,
                                (reportId,
                                 date_processed,
                                 0,
                                 "jqs@sun.com",
                                 "1.0"),
                                17),
                               {'date_processed':date_processed})
    fakeExtensionsTable.expect('insert',
                               (c.fakeCursor,
                                (reportId,
                                 date_processed,
                                 1,
                                 "this_addon_is_missing_its_version",
                                 None),
                                17),
                               {'date_processed':date_processed})
    fakeExtensionsTable.expect('insert',
                               (c.fakeCursor,
                                (reportId,
                                 date_processed,
                                 2,
                                 "avg@igeared",
                                 "2.507.024.001"),
                                17),
                               {'date_processed':date_processed})
    p.extensionsTable = fakeExtensionsTable
    r = p.insertAdddonsIntoDatabase(c.fakeCursor,
                                    reportId,
                                    jd,
                                    date_processed,
                                    error_list)
    e = [["jqs@sun.com", "1.0"],
         ["avg@igeared", "2.507.024.001"],
        ]
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)
    e = ['WARNING: "this_addon_is_missing_its_version" is deficient as a ' \
         'name and version for an addon']
    r = error_list
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testInsertCrashProcess1():
    """testInsertCrashProcess1: no processType"""
    p, c = getMockedProcessorAndContext()
    reportId = 123
    jd = sample_meta_json.copy()
    date_processed = dt.datetime(2011,2,15,1,0,0)
    error_list = []

    r = p.insertCrashProcess(c.fakeCursor,
                             reportId,
                             jd,
                             date_processed,
                             error_list)
    e = {}
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testInsertCrashProcess2():
    """testInsertCrashProcess2: not a plugin"""
    p, c = getMockedProcessorAndContext()
    reportId = 123
    jd = sample_meta_json.copy()
    jd['ProcessType'] = 'other'
    date_processed = dt.datetime(2011,2,15,1,0,0)
    error_list = []

    r = p.insertCrashProcess(c.fakeCursor,
                             reportId,
                             jd,
                             date_processed,
                             error_list)
    e = {'processType': 'other'}
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testInsertCrashProcess3():
    """testInsertCrashProcess3: plugin exists already in db"""
    p, c = getMockedProcessorAndContext()
    reportId = 123
    jd = sample_meta_json.copy()
    jd['ProcessType'] = 'plugin'
    jd['PluginFilename'] = 'aplugin.so'
    jd['PluginName'] = 'a plugin name'
    jd['PluginVersion'] = '1.0'
    date_processed = dt.datetime(2011,2,15,1,0,0)
    error_list = []

    c.fakeDatabaseModule.expect('singleRowSql',
                                (c.fakeCursor,
                                 'select id from plugins '
                                 'where filename = %s '
                                 'and name = %s',
                                 (jd['PluginFilename'],
                                  jd['PluginName'])),
                                {},
                                777)
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair',
                                        None,
                                        None,
                                        None)
    fakePluginsReportsTable = exp.DummyObjectWithExpectations()
    fakePluginsReportsTable.expect('insert',
                                   (c.fakeCursor,
                                    (reportId,
                                     777,
                                     date_processed,
                                     jd['PluginVersion']),
                                    None),
                                   {'date_processed':date_processed})
    p.pluginsReportsTable = fakePluginsReportsTable
    r = p.insertCrashProcess(c.fakeCursor,
                             reportId,
                             jd,
                             date_processed,
                             error_list)
    e = {'processType': 'plugin',
         'pluginFilename': jd['PluginFilename'],
         'pluginName': jd['PluginName'],
         'pluginVersion': jd['PluginVersion']
        }
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testInsertCrashProcess4():
    """testInsertCrashProcess4: plugin not already in db"""
    p, c = getMockedProcessorAndContext()
    reportId = 123
    jd = sample_meta_json.copy()
    jd['ProcessType'] = 'plugin'
    jd['PluginFilename'] = 'aplugin.so'
    jd['PluginName'] = 'a plugin name'
    jd['PluginVersion'] = '1.0'
    date_processed = dt.datetime(2011,2,15,1,0,0)
    error_list = []

    c.fakeDatabaseModule.expect('singleRowSql',
                                (c.fakeCursor,
                                 'select id from plugins '
                                 'where filename = %s '
                                 'and name = %s',
                                 (jd['PluginFilename'],
                                  jd['PluginName'])),
                                {},
                                None,
                                sdb.SQLDidNotReturnSingleRow())
    fakePluginsTable = exp.DummyObjectWithExpectations()
    fakePluginsTable.expect('insert',
                            (c.fakeCursor,
                             (jd['PluginFilename'],
                              jd['PluginName'])),
                            {})
    p.pluginsTable = fakePluginsTable
    c.fakeDatabaseModule.expect('singleRowSql',
                                (c.fakeCursor,
                                 'select id from plugins '
                                 'where filename = %s '
                                 'and name = %s',
                                 (jd['PluginFilename'],
                                  jd['PluginName'])),
                                {},
                                777)
    c.fakeDatabaseConnectionPool.expect('connectionCursorPair',
                                        None,
                                        None,
                                        None)
    fakePluginsReportsTable = exp.DummyObjectWithExpectations()
    fakePluginsReportsTable.expect('insert',
                                   (c.fakeCursor,
                                    (reportId,
                                     777,
                                     date_processed,
                                     jd['PluginVersion']),
                                    None),
                                   {'date_processed':date_processed})
    p.pluginsReportsTable = fakePluginsReportsTable
    r = p.insertCrashProcess(c.fakeCursor,
                             reportId,
                             jd,
                             date_processed,
                             error_list)
    e = {'processType': 'plugin',
         'pluginFilename': jd['PluginFilename'],
         'pluginName': jd['PluginName'],
         'pluginVersion': jd['PluginVersion']
        }
    assert r == e, 'expected\n%s\nbut got\n%s' % (e, r)

def testSubmitOoidToElasticSearch_1():
    """testSubmitOoidToElasticSearch_1: submit to ES with timeout"""
    import socket as s
    p, c = getMockedProcessorAndContext()
    uuid = 'ef38fe89-43b6-4cd4-b154-392022110607'
    salted_ooid = 'e110607ef38fe89-43b6-4cd4-b154-392022110607'
    fakeUrllib2 = exp.DummyObjectWithExpectations()
    fakeRequestObject = 17
    fakeUrllib2.expect('Request', (salted_ooid, {}), {}, fakeRequestObject)
    fakeFileLikeObject = exp.DummyObjectWithExpectations()
    fakeFileLikeObject.expect('read', (), {}, None, s.timeout)
    #fakeSocketModule = exp.DummyObjectWithExpectations()
    #fakeSocketModule.expect('timeout', returnValue=socket.timeout)
    fakeUrllib2.expect('urlopen', (17,), {'timeout':2}, fakeFileLikeObject)
    fakeUrllib2.expect('socket', returnValue=s)
    p.submitOoidToElasticSearch(uuid, fakeUrllib2)

def testSubmitOoidToElasticSearch_2():
    """testSubmitOoidToElasticSearch_2: submit to ES - success"""
    import socket as s
    p, c = getMockedProcessorAndContext()
    uuid = 'ef38fe89-43b6-4cd4-b154-392022110607'
    salted_ooid = 'e110607ef38fe89-43b6-4cd4-b154-392022110607'
    fakeUrllib2 = exp.DummyObjectWithExpectations()
    fakeRequestObject = 17
    fakeUrllib2.expect('Request', (salted_ooid, {}), {}, fakeRequestObject)
    fakeFileLikeObject = exp.DummyObjectWithExpectations()
    fakeFileLikeObject.expect('read', (), {}, None)
    fakeUrllib2.expect('urlopen', (17,), {'timeout':2}, fakeFileLikeObject)
    p.submitOoidToElasticSearch(uuid, fakeUrllib2)

def testSubmitOoidToElasticSearch_3():
    """testSubmitOoidToElasticSearch_3: submit to ES with utter failure"""
    import socket as s
    p, c = getMockedProcessorAndContext()
    uuid = 'ef38fe89-43b6-4cd4-b154-392022110607'
    salted_ooid = 'e110607ef38fe89-43b6-4cd4-b154-392022110607'
    fakeUrllib2 = exp.DummyObjectWithExpectations()
    fakeRequestObject = 17
    fakeUrllib2.expect('Request', (salted_ooid, {}), {}, fakeRequestObject)
    fakeFileLikeObject = exp.DummyObjectWithExpectations()
    fakeFileLikeObject.expect('read', (), {}, None, Exception)
    #fakeSocketModule = exp.DummyObjectWithExpectations()
    #fakeSocketModule.expect('timeout', returnValue=socket.timeout)
    fakeUrllib2.expect('urlopen', (17,), {'timeout':2}, fakeFileLikeObject)
    fakeUrllib2.expect('socket', returnValue=s)
    p.submitOoidToElasticSearch(uuid, fakeUrllib2)


