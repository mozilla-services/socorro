import socorro.processor.registration as reg
import socorro.database.database as sdb
import socorro.lib.util as sutil
import socorro.unittest.testlib.expectations as exp
import socorro.lib.ConfigurationManager as scm

import datetime as dt


def expected_assert(expected, got):
    assert expected == got, 'expected\n%s\nbut got\n%s' % (expected, got)


def test_constructor():
    conf = sutil.DotDict()
    conf.logger = 17
    db_conn_source = 32

    class MyRegister(reg.ProcessorRegistrationAgent):
        def __init__(self, config, db_conn_source):
            super(MyRegister, self).__init__(config, db_conn_source)
            self.registration_called = False

        def registration(self):
            self.registration_called = True

    r = MyRegister(conf, db_conn_source)
    expected_assert(conf, r.config)
    expected_assert(db_conn_source, r.db_pool)
    expected_assert(dt.datetime(1999, 1, 1), r.last_checkin_ts)
    expected_assert(17, r.logger)
    expected_assert(dt.datetime.now, r.now_func)
    assert not r.registration_called, 'registration function not called'


class MockedRegister(reg.ProcessorRegistrationAgent):
    def __init__(self, config, db_conn_source, now_func, os, sdb):
        self.new_identity_called = False
        self.specific_identity_called = False
        self.any_identity_called = False
        self.identity_by_host_called = False
        super(MockedRegister, self).__init__(config, db_conn_source,
                                             now_func, os, sdb)

    def assume_new_identity(self, cursor, threshold, hostname, id):
        self.new_identity_called = True
        return 666

    def assume_specific_identity(self, cursor, threshold, hostname, id):
        self.specific_identity_called = True
        return id

    def assume_any_identity(self, cursor, threshold, hostname, id):
        self.any_identity_called = True
        return 314

    def assume_identity_by_host(self, cursor, threshold, hostname, id):
        self.identity_by_host_called = True
        return 938


def now_func():
    return dt.datetime(2011, 8, 23, 10, 0, 0)


def setup_mocked_register(register_class):
    conf = sutil.DotDict()
    conf.processorCheckInTime = dt.timedelta(0, 300)
    conf.processorCheckInFrequency = dt.timedelta(0, 300)
    conf.processorId = 17
    fake_logger = exp.DummyObjectWithExpectations()
    conf.logger = fake_logger
    threshold = now_func() + conf.processorCheckInTime
    os_module = exp.DummyObjectWithExpectations()
    sdb_module = exp.DummyObjectWithExpectations()
    db_conn = exp.DummyObjectWithExpectations()
    db_cur = exp.DummyObjectWithExpectations()
    db_pool = exp.DummyObjectWithExpectations()

    fake_logger.expect('info', ('connecting to database',), {})
    db_pool.expect('connectionCursorPair', (), {}, (db_conn, db_cur))
    os_module.expect('uname', (), {}, ['a', 'b', 'c'])
    os_module.expect('getpid', (), {}, 1111)
    sdb_module.expect('singleValueSql', (db_cur,
                                         register_class.NOW_SQL,
                                         (conf.processorCheckInTime,)),
                                        {},
                                        threshold)
    fake_logger.expect('info', ("registering with 'processors' table",),
                               {})
    db_conn.expect('commit', (), {})

    return register_class(conf, db_pool, now_func, os_module, sdb_module)


def test_registration_for_new_identity():
    class MyRegister(MockedRegister):
        def __init__(self, config, db_conn_source, now_func, os, sdb):
            super(MyRegister, self).__init__(config, db_conn_source,
                                             now_func, os, sdb)

        @staticmethod
        def requested_processor_id(requested_id):
            return 0  # force "new identity"
    r = setup_mocked_register(MyRegister)
    expected_assert('b_1111', r.processor_name)
    assert r.new_identity_called, ("expected 'assume_new_identity' to be "
                                   "called, but it wasn't")
    assert not r.specific_identity_called, ("'assume_specific_identity' "
                                            "should not have been called")
    assert not r.any_identity_called, ("'assume_any_identity' "
                                       "should not have been called")
    assert not r.identity_by_host_called, ("'assume_identity_by_host' "
                                           "should not have been called")


def test_registration_for_specific_identity():
    class MyRegister(MockedRegister):
        def __init__(self, config, db_conn_source, now_func, os, sdb):
            super(MyRegister, self).__init__(config, db_conn_source,
                                             now_func, os, sdb)

        @staticmethod
        def requested_processor_id(requested_id):
            return 11  # force "specific_identity"
    r = setup_mocked_register(MyRegister)
    expected_assert('b_1111', r.processor_name)
    assert not r.new_identity_called, ("'assume_new_identity' should not"
                                       "have been called")
    assert r.specific_identity_called, ("'assume_specific_identity' "
                                        "should have been called, but was not")
    assert not r.any_identity_called, ("'assume_any_identity' "
                                       "should not have been called")
    assert not r.identity_by_host_called, ("'assume_identity_by_host' "
                                           "should not have been called")


def test_registration_for_any_identity():
    class MyRegister(MockedRegister):
        def __init__(self, config, db_conn_source, now_func, os, sdb):
            super(MyRegister, self).__init__(config, db_conn_source,
                                             now_func, os, sdb)

        @staticmethod
        def requested_processor_id(requested_id):
            return 'auto'  # force "any_identity"
    r = setup_mocked_register(MyRegister)
    expected_assert('b_1111', r.processor_name)
    assert not r.new_identity_called, ("'assume_new_identity' should not"
                                       "have been called")
    assert not r.specific_identity_called, ("'assume_specific_identity' "
                                            "should not have been called")
    assert r.any_identity_called, ("'assume_any_identity' "
                                   "should have been called, but was not")
    assert not r.identity_by_host_called, ("'assume_identity_by_host' "
                                           "should not have been called")


def test_registration_for_identity_by_host():
    class MyRegister(MockedRegister):
        def __init__(self, config, db_conn_source, now_func, os, sdb):
            super(MyRegister, self).__init__(config, db_conn_source,
                                             now_func, os, sdb)

        @staticmethod
        def requested_processor_id(requested_id):
            return 'host'  # force "identity_by_host"
    r = setup_mocked_register(MyRegister)
    expected_assert('b_1111', r.processor_name)
    assert not r.new_identity_called, ("'assume_new_identity' should not"
                                       "have been called")
    assert not r.specific_identity_called, ("'assume_specific_identity' "
                                            "should not have been called")
    assert not r.any_identity_called, ("'assume_any_identity' "
                                       "should not have been called")
    assert r.identity_by_host_called, ("'assume_identity_by_host' "
                                       "should have been called, but was not")


def test_assume_identity_by_host_1():
    conf = sutil.DotDict()
    fake_logger = exp.DummyObjectWithExpectations()
    conf.logger = fake_logger
    conf.processorCheckInTime = dt.timedelta(0, 300)
    threshold = now_func() + conf.processorCheckInTime
    os_module = exp.DummyObjectWithExpectations()
    sdb_module = exp.DummyObjectWithExpectations()
    db_conn = exp.DummyObjectWithExpectations()
    db_cur = exp.DummyObjectWithExpectations()
    db_pool = exp.DummyObjectWithExpectations()
    hostname = 'fred'

    class MyRegister(reg.ProcessorRegistrationAgent):
        def __init__(self, config, db_conn_source, now_func, os, sdb):
            super(MyRegister, self).__init__(config, db_conn_source,
                                             now_func, os, sdb)

        def take_over_dead_processor(self, cursor, proc_id):
            expected_assert(db_cur, cursor)
            expected_assert(proc_id, 17)

        def registration(self):
            pass

    fake_logger.expect('debug',
                       ('looking for a dead processor for host %s', 'fred'),
                       {})
    sql = ("select id from processors"
           " where lastseendatetime < %s"
           " and name like %s limit 1")
    sdb_module.expect('singleValueSql',
                      (db_cur, sql, (threshold, hostname + '%')),
                      {},
                      17)
    fake_logger.expect('info',
                       ('will step in for processor %d', 17), {})

    r = MyRegister(conf, db_pool, now_func, os_module, sdb_module)
    id = r.assume_identity_by_host(db_cur, threshold, hostname, 17)
    expected_assert(17, id)


def test_assume_identity_by_host_2():
    conf = sutil.DotDict()
    fake_logger = exp.DummyObjectWithExpectations()
    conf.logger = fake_logger
    conf.processorCheckInTime = dt.timedelta(0, 300)
    threshold = now_func() + conf.processorCheckInTime
    os_module = exp.DummyObjectWithExpectations()
    sdb_module = exp.DummyObjectWithExpectations()
    db_conn = exp.DummyObjectWithExpectations()
    db_cur = exp.DummyObjectWithExpectations()
    db_pool = exp.DummyObjectWithExpectations()
    hostname = 'fred'

    class MyRegister(reg.ProcessorRegistrationAgent):
        def __init__(self, config, db_conn_source, now_func, os, sdb):
            super(MyRegister, self).__init__(config, db_conn_source,
                                             now_func, os, sdb)

        def take_over_dead_processor(self, cursor, proc_id):
            expected_assert(db_cur, cursor)
            expected_assert(proc_id, 17)

        def registration(self):
            pass

    fake_logger.expect('debug',
                       ('looking for a dead processor for host %s', 'fred'),
                       {})
    sql = ("select id from processors"
           " where lastseendatetime < %s"
           " and name like %s limit 1")
    sdb_module.expect('singleValueSql',
                      (db_cur, sql, (threshold, hostname + '%')),
                      {},
                      None,
                      sdb.SQLDidNotReturnSingleValue)
    fake_logger.expect('debug',
                       ("no dead processor found for host, %s", hostname), {})
    sql2 = "select id from processors where name like 'fred%'"
    sdb_module.expect('singleValueSql',
                      (db_cur, sql2),
                      {},
                      836)
    r = MyRegister(conf, db_pool, now_func, os_module, sdb_module)
    try:
        id = r.assume_identity_by_host(db_cur, threshold, hostname, 17)
    except reg.RegistrationError:
        assert True
    except Exception, x:
        assert False, "didn't expect %s exception" % str(x)
    else:
        assert False, "expected a sdb.SQLDidNotReturnSingleValue"


def test_assume_identity_by_host_3():
    conf = sutil.DotDict()
    fake_logger = exp.DummyObjectWithExpectations()
    conf.logger = fake_logger
    conf.processorCheckInTime = dt.timedelta(0, 300)
    threshold = now_func() + conf.processorCheckInTime
    os_module = exp.DummyObjectWithExpectations()
    sdb_module = exp.DummyObjectWithExpectations()
    db_conn = exp.DummyObjectWithExpectations()
    db_cur = exp.DummyObjectWithExpectations()
    db_pool = exp.DummyObjectWithExpectations()
    hostname = 'fred'

    class MyRegister(reg.ProcessorRegistrationAgent):
        def __init__(self, config, db_conn_source, now_func, os, sdb):
            super(MyRegister, self).__init__(config, db_conn_source,
                                             now_func, os, sdb)

        def take_over_dead_processor(self, cursor, proc_id):
            expected_assert(db_cur, cursor)
            expected_assert(proc_id, 17)

        def assume_new_identity(self, cursor, thresh, host, proc_id):
            expected_assert(db_cur, cursor)
            expected_assert(threshold, thresh)
            expected_assert(hostname, host)
            expected_assert(proc_id, 17)
            return proc_id

        def registration(self):
            pass

    fake_logger.expect('debug',
                       ('looking for a dead processor for host %s', 'fred'),
                       {})
    sql = ("select id from processors"
           " where lastseendatetime < %s"
           " and name like %s limit 1")
    sdb_module.expect('singleValueSql',
                      (db_cur, sql, (threshold, hostname + '%')),
                      {},
                      None,
                      sdb.SQLDidNotReturnSingleValue)
    fake_logger.expect('debug',
                       ("no dead processor found for host, %s", hostname), {})
    sql2 = "select id from processors where name like 'fred%'"
    sdb_module.expect('singleValueSql',
                      (db_cur, sql2),
                      {},
                      None,
                      sdb.SQLDidNotReturnSingleValue)
    r = MyRegister(conf, db_pool, now_func, os_module, sdb_module)
    id = r.assume_identity_by_host(db_cur, threshold, hostname, 17)
    expected_assert(17, id)


def test_assume_any_identity_1():
    conf = sutil.DotDict()
    fake_logger = exp.DummyObjectWithExpectations()
    conf.logger = fake_logger
    conf.processorCheckInTime = dt.timedelta(0, 300)
    threshold = now_func() + conf.processorCheckInTime
    os_module = exp.DummyObjectWithExpectations()
    sdb_module = exp.DummyObjectWithExpectations()
    db_conn = exp.DummyObjectWithExpectations()
    db_cur = exp.DummyObjectWithExpectations()
    db_pool = exp.DummyObjectWithExpectations()
    hostname = 'fred'

    class MyRegister(reg.ProcessorRegistrationAgent):
        def __init__(self, config, db_conn_source, now_func, os, sdb):
            super(MyRegister, self).__init__(config, db_conn_source,
                                             now_func, os, sdb)

        def take_over_dead_processor(self, cursor, proc_id):
            expected_assert(db_cur, cursor)
            expected_assert(proc_id, 17)

        def registration(self):
            pass

    fake_logger.expect('debug',
                       ('looking for any dead processor',),
                       {})
    sql = ("select id from processors"
           " where lastseendatetime < %s limit 1")
    sdb_module.expect('singleValueSql',
                      (db_cur, sql, (threshold,)),
                      {},
                      17)
    fake_logger.expect('info',
                       ('will step in for processor %d', 17), {})

    r = MyRegister(conf, db_pool, now_func, os_module, sdb_module)
    id = r.assume_any_identity(db_cur, threshold, hostname, 17)
    expected_assert(17, id)


def test_assume_any_identity_2():
    conf = sutil.DotDict()
    fake_logger = exp.DummyObjectWithExpectations()
    conf.logger = fake_logger
    conf.processorCheckInTime = dt.timedelta(0, 300)
    threshold = now_func() + conf.processorCheckInTime
    os_module = exp.DummyObjectWithExpectations()
    sdb_module = exp.DummyObjectWithExpectations()
    db_conn = exp.DummyObjectWithExpectations()
    db_cur = exp.DummyObjectWithExpectations()
    db_pool = exp.DummyObjectWithExpectations()
    hostname = 'fred'

    class MyRegister(reg.ProcessorRegistrationAgent):
        def __init__(self, config, db_conn_source, now_func, os, sdb):
            super(MyRegister, self).__init__(config, db_conn_source,
                                             now_func, os, sdb)

        def take_over_dead_processor(self, cursor, proc_id):
            expected_assert(db_cur, cursor)
            expected_assert(proc_id, 17)

        def assume_new_identity(self, cursor, thresh, host, proc_id):
            expected_assert(db_cur, cursor)
            expected_assert(threshold, thresh)
            expected_assert(hostname, host)
            expected_assert(proc_id, 17)
            return proc_id

        def registration(self):
            pass

    fake_logger.expect('debug',
                       ('looking for any dead processor',),
                       {})
    sql = ("select id from processors"
           " where lastseendatetime < %s limit 1")
    sdb_module.expect('singleValueSql',
                      (db_cur, sql, (threshold,)),
                      {},
                      None,
                      sdb.SQLDidNotReturnSingleValue)
    fake_logger.expect('debug',
                       ("no dead processor found, registering as new",), {})

    r = MyRegister(conf, db_pool, now_func, os_module, sdb_module)
    id = r.assume_any_identity(db_cur, threshold, hostname, 17)
    expected_assert(17, id)


def test_assume_specific_identity_1():
    conf = sutil.DotDict()
    fake_logger = exp.DummyObjectWithExpectations()
    conf.logger = fake_logger
    conf.processorCheckInTime = dt.timedelta(0, 300)
    threshold = now_func() + conf.processorCheckInTime
    os_module = exp.DummyObjectWithExpectations()
    sdb_module = exp.DummyObjectWithExpectations()
    db_conn = exp.DummyObjectWithExpectations()
    db_cur = exp.DummyObjectWithExpectations()
    db_pool = exp.DummyObjectWithExpectations()
    hostname = 'fred'

    class MyRegister(reg.ProcessorRegistrationAgent):
        def __init__(self, config, db_conn_source, now_func, os, sdb):
            super(MyRegister, self).__init__(config, db_conn_source,
                                             now_func, os, sdb)

        def take_over_dead_processor(self, cursor, proc_id):
            expected_assert(db_cur, cursor)
            expected_assert(proc_id, 17)

        def registration(self):
            pass

    fake_logger.expect('debug',
                       ('looking for a specific dead processor',),
                       {})
    sql = ("select id from processors "
           "where lastSeenDateTime < %s "
           "and id = %s")
    sdb_module.expect('singleValueSql',
                      (db_cur, sql, (threshold, 17)),
                      {},
                      17)
    fake_logger.expect('info',
                       ('stepping in for processor %d', 17), {})

    r = MyRegister(conf, db_pool, now_func, os_module, sdb_module)
    id = r.assume_specific_identity(db_cur, threshold, hostname, 17)
    expected_assert(17, id)


def test_assume_specific_identity_2():
    conf = sutil.DotDict()
    fake_logger = exp.DummyObjectWithExpectations()
    conf.logger = fake_logger
    conf.processorCheckInTime = dt.timedelta(0, 300)
    threshold = now_func() + conf.processorCheckInTime
    os_module = exp.DummyObjectWithExpectations()
    sdb_module = exp.DummyObjectWithExpectations()
    db_conn = exp.DummyObjectWithExpectations()
    db_cur = exp.DummyObjectWithExpectations()
    db_pool = exp.DummyObjectWithExpectations()
    hostname = 'fred'

    class MyRegister(reg.ProcessorRegistrationAgent):
        def __init__(self, config, db_conn_source, now_func, os, sdb):
            super(MyRegister, self).__init__(config, db_conn_source,
                                             now_func, os, sdb)

        def take_over_dead_processor(self, cursor, proc_id):
            expected_assert(db_cur, cursor)
            expected_assert(proc_id, 17)

        def registration(self):
            pass

    fake_logger.expect('debug',
                       ('looking for a specific dead processor',),
                       {})
    sql = ("select id from processors "
           "where lastSeenDateTime < %s "
           "and id = %s")
    sdb_module.expect('singleValueSql',
                      (db_cur, sql, (threshold, 17)),
                      {},
                      None,
                      sdb.SQLDidNotReturnSingleValue)
    #fake_logger.expect('info',
                       #('stepping in for processor %d', 17), {})

    r = MyRegister(conf, db_pool, now_func, os_module, sdb_module)
    try:
        id = r.assume_specific_identity(db_cur, threshold, hostname, 17)
    except reg.RegistrationError:
        assert True
    except Exception, x:
        assert False, "%s exception was not expected" % str(x)
    else:
        assert False, "a RegistrationError was expected, but didn't happen"


def test_assume_new_identity():
    conf = sutil.DotDict()
    fake_logger = exp.DummyObjectWithExpectations()
    conf.logger = fake_logger
    conf.processorCheckInTime = dt.timedelta(0, 300)
    threshold = now_func() + conf.processorCheckInTime
    os_module = exp.DummyObjectWithExpectations()
    sdb_module = exp.DummyObjectWithExpectations()
    db_conn = exp.DummyObjectWithExpectations()
    db_cur = exp.DummyObjectWithExpectations()
    db_pool = exp.DummyObjectWithExpectations()
    hostname = 'fred'

    class MyRegister(reg.ProcessorRegistrationAgent):
        def __init__(self, config, db_conn_source, now_func, os, sdb):
            super(MyRegister, self).__init__(config, db_conn_source,
                                             now_func, os, sdb)

        def registration(self):
            self.processor_name = 'fred'

    fake_logger.expect('debug',
                       ('becoming a new processor',),
                       {})
    sql = ("insert into processors"
           "    (id,"
           "     name,"
           "     startdatetime,"
           "     lastseendatetime) "
           "values"
           "    (default,"
           "     %s,"
           "     now(),"
           "     now()) "
           "returning id")
    sdb_module.expect('singleValueSql',
                      (db_cur, sql, ('fred',)),
                      {},
                      17)

    r = MyRegister(conf, db_pool, now_func, os_module, sdb_module)
    id = r.assume_new_identity(db_cur, threshold, hostname, 17)
    expected_assert(17, id)


def test_take_over_dead_processor():
    conf = sutil.DotDict()
    fake_logger = exp.DummyObjectWithExpectations()
    conf.logger = fake_logger
    conf.processorCheckInTime = dt.timedelta(0, 300)
    threshold = now_func() + conf.processorCheckInTime
    os_module = exp.DummyObjectWithExpectations()
    sdb_module = exp.DummyObjectWithExpectations()
    db_conn = exp.DummyObjectWithExpectations()
    db_cur = exp.DummyObjectWithExpectations()
    db_pool = exp.DummyObjectWithExpectations()
    hostname = 'fred'

    class MyRegister(reg.ProcessorRegistrationAgent):
        def __init__(self, config, db_conn_source, now_func, os, sdb):
            super(MyRegister, self).__init__(config, db_conn_source,
                                             now_func, os, sdb)

        def registration(self):
            self.processor_name = 'fred'

    fake_logger.expect('debug',
                       ('taking over a dead processor',),
                       {})
    sql = ("update processors set name = %s, "
           "startdatetime = now(), lastseendatetime = now()"
           " where id = %s")
    db_cur.expect('execute',
                  (sql, ('fred', 17)),
                  {},
                  17)
    sql2 = ("update jobs set"
            "    starteddatetime = NULL,"
            "    completeddatetime = NULL,"
            "    success = NULL "
            "where"
            "    owner = %s")
    db_cur.expect('execute',
                  (sql2, (17,)),
                  {},
                  17)

    r = MyRegister(conf, db_pool, now_func, os_module, sdb_module)
    id = r.take_over_dead_processor(db_cur, 17)
    assert id is None, "expected None but got %s" % id


def test_requested_processor_id():
    r = setup_mocked_register(MockedRegister)
    i = r.requested_processor_id(0)
    expected_assert(0, i)
    i = r.requested_processor_id(1)
    expected_assert(1, i)
    i = r.requested_processor_id('host')
    expected_assert('host', i)
    i = r.requested_processor_id('auto')
    expected_assert('auto', i)
    try:
        i = r.requested_processor_id('fred')
    except scm.OptionError, x:
        expected_assert("'fred' is not a valid value", str(x))
    except Exception, x:
        assert False, "expected scm.OptionError, but got '%s'" % str(x)
    else:
        assert False, "expected scm.OptionError, but got no exception"


def test_checkin():
    def now_func():
        return dt.datetime(2011, 1, 1, 0, 6, 0)
    conf = sutil.DotDict()
    conf.processorCheckInTime = dt.timedelta(0, 300)
    conf.processorCheckInFrequency = dt.timedelta(0, 300)
    conf.processorId = 17
    fake_logger = exp.DummyObjectWithExpectations()
    conf.logger = fake_logger
    threshold = now_func() + conf.processorCheckInTime
    os_module = exp.DummyObjectWithExpectations()
    sdb_module = exp.DummyObjectWithExpectations()
    db_conn = exp.DummyObjectWithExpectations()
    db_cur = exp.DummyObjectWithExpectations()
    db_pool = exp.DummyObjectWithExpectations()

    fake_logger.expect('info', ('connecting to database',), {})
    db_pool.expect('connectionCursorPair', (), {}, (db_conn, db_cur))
    os_module.expect('uname', (), {}, ['a', 'b', 'c'])
    os_module.expect('getpid', (), {}, 1111)
    sdb_module.expect('singleValueSql', (db_cur,
                                        reg.ProcessorRegistrationAgent.NOW_SQL,
                                        (conf.processorCheckInTime,)),
                                        {},
                                        threshold)
    fake_logger.expect('info', ("registering with 'processors' table",),
                               {})
    db_conn.expect('commit', (), {})
    fake_logger.expect('debug', ("updating 'processor' table registration",),
                       {})
    db_pool.expect('connectionCursorPair', (), {}, (db_conn, db_cur))
    db_cur.expect('execute', ("update processors set lastseendatetime = %s "
                  "where id = %s", (now_func(), 17)), {})
    db_conn.expect('commit', (), {})
    r = MockedRegister(conf, db_pool, now_func, os_module, sdb_module)
    r.checkin()
    expected_assert(now_func(), r.last_checkin_ts)
    r.last_checkin_ts = dt.datetime(2011, 1, 1, 0, 6, 0)
    r.checkin()
    r.last_checkin_ts = dt.datetime(2011, 1, 1, 0, 5, 0)
    r.checkin()
    r.last_checkin_ts = dt.datetime(2011, 1, 1, 0, 4, 0)
    r.checkin()
    r.last_checkin_ts = dt.datetime(2011, 1, 1, 0, 3, 0)
    r.checkin()
    r.last_checkin_ts = dt.datetime(2011, 1, 1, 0, 2, 0)
    r.checkin()
    r.last_checkin_ts = dt.datetime(2011, 1, 1, 0, 1, 0)
    r.checkin()
    fake_logger.expect('debug', ("updating 'processor' table registration",),
                       {})
    db_pool.expect('connectionCursorPair', (), {}, (db_conn, db_cur))
    db_cur.expect('execute', ("update processors set lastseendatetime = %s "
                  "where id = %s", (now_func(), 17)), {})
    db_conn.expect('commit', (), {})
    r.last_checkin_ts = dt.datetime(2011, 1, 1, 0, 0, 0)
    r.checkin()
    expected_assert(now_func(), r.last_checkin_ts)
