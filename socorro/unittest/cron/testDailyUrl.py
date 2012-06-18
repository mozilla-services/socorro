# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

import datetime as dt

import socorro.lib.util as sutil
import socorro.cron.dailyUrl as dailyUrl
import socorro.unittest.testlib.expectations as exp

#-------------------------------------------------------------------------------
def test_write_row_1():
    """test_write_row_1 - write private only"""
    row = [x for x in xrange(27)]
    private_file_handle = exp.DummyObjectWithExpectations()
    private_file_handle.expect('writerow', (row,), {})
    public_file_handle = None
    dailyUrl.write_row((private_file_handle, public_file_handle), row)

#-------------------------------------------------------------------------------
def test_write_row_2():
    """test_write_row_2 - write both public and private"""
    row = [x for x in xrange(28)]
    private_file_handle = exp.DummyObjectWithExpectations()
    private_file_handle.expect('writerow', (row,), {})
    public_row = [x for x in xrange(28)]
    public_row[1] = 'URL (removed)'
    public_row[17] = ''
    public_file_handle = exp.DummyObjectWithExpectations()
    public_file_handle.expect('writerow', (public_row,), {})
    dailyUrl.write_row((private_file_handle, public_file_handle), row)

#-------------------------------------------------------------------------------
raw_row = range(28)
raw_row[0] = 'xyz'
raw_row[1] = 'http://xyz.com'
raw_row[2] = 'http://crash-stats.mozilla.com/report/index/abcd289c-a4e0-496a-a120-beb6d2101225\r\n'
raw_row[3] = '201012250610'
raw_row[4] = '201012250620'
raw_row[5] = '2010-10-10'
raw_row[6] = 'Firefloozy'
raw_row[7] = '5.0'
raw_row[8] = '20101210'
raw_row[9] = '1.9.1'
raw_row[10] = '  Windows NT  '
raw_row[11] = '4.0'
raw_row[12] = 'FredCPU | 13bit'
raw_row[13] = '0x0001'
raw_row[14] = ['1234','5678']
raw_row[15] = 'this sucks\tbut I love you anyway'
raw_row[16] = 10
raw_row[17] = 'fred@mozilla.com'
raw_row[18] = 1222
raw_row[19] = 'fred.c'
raw_row[20] = 'not'
raw_row[21] = None
raw_row[22] = '12345'
raw_row[23] = 'I said so'
raw_row[24] = 'plugin'
raw_row[25] = 'app_notes'
raw_row[26] = 233333
raw_row[27] = '123123123'

exp_row = range(28)
exp_row[0] = 'xyz'
exp_row[1] = 'http://xyz.com'
exp_row[2] = 'http://crash-stats.mozilla.com/report/index/abcd289c-a4e0-496a-a120-beb6d2101225'
exp_row[3] = '201012250610'
exp_row[4] = '201012250620'
exp_row[5] = '2010-10-10'
exp_row[6] = 'Firefloozy'
exp_row[7] = '5.0'
exp_row[8] = '20101210'
exp_row[9] = '1.9.1'
exp_row[10] = 'Windows NT'
exp_row[11] = 'XXX'
exp_row[12] = 'FredCPU | 13bit'
exp_row[13] = '0x0001'
exp_row[14] = '1234,5678'
exp_row[15] = 'this sucks but I love you anyway'
exp_row[16] = 10
exp_row[17] = 'yes'
exp_row[18] = 1222
exp_row[19] = 'fred.c'
exp_row[20] = 'not'
exp_row[21] = '\\N'
exp_row[22] = '12345'
exp_row[23] = 'I said so'
exp_row[24] = 'plugin'
exp_row[25] = 'app_notes'
exp_row[26] = 233333
exp_row[27] = '123123123'
#-------------------------------------------------------------------------------
def test_process_crash():
    """test_process_crash - test record fixups"""
    id_cache = exp.DummyObjectWithExpectations()
    id_cache.expect('getAppropriateOsVersion', ('Windows NT', '4.0'), {}, 'XXX')
    result = dailyUrl.process_crash(raw_row, id_cache)
    exp.assert_expected(result, exp_row)

#-------------------------------------------------------------------------------
def test_gzipped_csv_files_1():
    """test_gzipped_csv_files_1 - test the gzip/csv context manager"""
    conf = sutil.DotDict()
    conf.day = dt.date(2011, 1, 25)
    conf.outputPath = './'
    conf.publicOutputPath = './pub'
    fake_csv_module = exp.DummyObjectWithExpectations()
    fake_gzip_module = exp.DummyObjectWithExpectations()

    fake_private_gzip_file_handle = exp.DummyObjectWithExpectations()
    fake_gzip_module.expect('open', ('./20110125-crashdata.csv.gz', 'w'), {},
                            fake_private_gzip_file_handle)
    fake_private_csv_file_handle = exp.DummyObjectWithExpectations()
    fake_csv_module.expect('writer',
                           (fake_private_gzip_file_handle,),
                           {'delimiter' : '\t', 'lineterminator' : '\n'},
                           fake_private_csv_file_handle)

    fake_public_gzip_file_handle = exp.DummyObjectWithExpectations()
    fake_gzip_module.expect('open', ('./pub/20110125-pub-crashdata.csv.gz', 'w'),
                            {},
                            fake_public_gzip_file_handle)
    fake_public_csv_file_handle = exp.DummyObjectWithExpectations()
    fake_csv_module.expect('writer',
                           (fake_public_gzip_file_handle,),
                           {'delimiter' : '\t', 'lineterminator' : '\n'},
                           fake_public_csv_file_handle)

    fake_private_gzip_file_handle.expect('close', (), {})
    fake_public_gzip_file_handle.expect('close', (), {})

    with dailyUrl.gzipped_csv_files(conf, fake_gzip_module, fake_csv_module) as t:
        assert t[0] is fake_private_csv_file_handle
        assert t[1] is fake_public_csv_file_handle

#-------------------------------------------------------------------------------
def test_gzipped_csv_files_2():
    """test_gzipped_csv_files_2 - test the gzip/csv context manager no public"""
    conf = sutil.DotDict()
    conf.day = dt.date(2011, 1, 25)
    conf.outputPath = './'
    fake_csv_module = exp.DummyObjectWithExpectations()
    fake_gzip_module = exp.DummyObjectWithExpectations()

    fake_private_gzip_file_handle = exp.DummyObjectWithExpectations()
    fake_gzip_module.expect('open', ('./20110125-crashdata.csv.gz', 'w'), {},
                            fake_private_gzip_file_handle)
    fake_private_csv_file_handle = exp.DummyObjectWithExpectations()
    fake_csv_module.expect('writer',
                           (fake_private_gzip_file_handle,),
                           {'delimiter' : '\t', 'lineterminator' : '\n'},
                           fake_private_csv_file_handle)

    fake_private_gzip_file_handle.expect('close', (), {})

    with dailyUrl.gzipped_csv_files(conf, fake_gzip_module, fake_csv_module) as t:
        assert t[0] is fake_private_csv_file_handle
        assert t[1] is None

#-------------------------------------------------------------------------------
def test_setup_query_parameters_1():
    """setup_query_parameters_1 - does it make the right query for single product"""
    conf = sutil.DotDict()
    conf.day = dt.date(2011, 1, 25)
    conf.product = 'Firefloozy'
    conf.version = ''
    result = dailyUrl.setup_query_parameters(conf)
    exp.assert_expected(result.now_str, "2011-01-26")
    exp.assert_expected(result.yesterday_str, "2011-01-25")
    exp.assert_expected(result.prod_phrase, "and r.product = 'Firefloozy'")
    exp.assert_expected(result.ver_phrase, "")

#-------------------------------------------------------------------------------
def test_setup_query_parameters_2():
    """setup_query_parameters_2 - does it make the right query for multiple products"""
    conf = sutil.DotDict()
    conf.day = dt.date(2011, 1, 25)
    conf.product = 'Firefloozy,Thunderthigh'
    conf.version = ''
    result = dailyUrl.setup_query_parameters(conf)
    exp.assert_expected(result.now_str, "2011-01-26")
    exp.assert_expected(result.yesterday_str, "2011-01-25")
    exp.assert_expected(result.prod_phrase, "and r.product in ('Firefloozy',"
                                            "'Thunderthigh')")
    exp.assert_expected(result.ver_phrase, "")


#-------------------------------------------------------------------------------
def test_dailyUrlDump():
    """test_dailyUrlDump - test the thing that ropes them all together"""
    conf = sutil.DotDict()
    conf.day = dt.date(2011, 1, 25)
    conf.product = 'Firefloozy,Thunderthigh'
    conf.version = ''
    sql_param = sutil.DotDict()
    sql_param.now_str = "2011-01-26"
    sql_param.yesterday_str = "2011-01-25"
    sql_param.prod_phrase = "and r.product in ('Firefloozy','Thunderthigh')"
    sql_param.ver_phrase = ""
    expected_sql = dailyUrl.sql % sql_param

    fake_logger = exp.DummyObjectWithExpectations()
    fake_logger.expect('debug', ("config.day = %s; now = %s; yesterday = %s",
                                 conf.day, "2011-01-26", "2011-01-25"), {})
    fake_logger.expect('debug', ("SQL is: %s", expected_sql), {})

    fake_database_module = exp.DummyObjectWithExpectations()
    fake_database_pool = exp.DummyObjectWithExpectations()
    fake_database_module.expect('DatabaseConnectionPool',
                                (conf, fake_logger), {}, fake_database_pool)
    fake_database_connection = exp.DummyObjectWithExpectations()
    fake_database_cursor = exp.DummyObjectWithExpectations()
    fake_database_pool.expect('connectionCursorPair', (), {},
                              (fake_database_connection, fake_database_cursor))
    def fake_gzipped_file_context_manager(config):
        yield (1, 2)
    fake_IdCache = exp.DummyObjectWithExpectations()
    fake_IdCache.expect('__call__', (fake_database_cursor,), {}, 'id_cache')
    fake_database_module.expect('execute', (fake_database_cursor, expected_sql),
                                {}, [1,2,3])
    fake_write_row = exp.DummyObjectWithExpectations()
    fake_database_cursor.expect('description', returnValue=['col','col2'])
    fake_write_row.expect('__call__', ((1,2), ['col','col2']), {})

    fake_process_crash = exp.DummyObjectWithExpectations()
    fake_process_crash.expect('__call__', (1, fake_IdCache), {}, [1, 1, 1])
    fake_write_row.expect('__call__', ((1,2), [1, 1, 1]), {})
    fake_process_crash.expect('__call__', (2, fake_IdCache), {}, [2, 2, 2])
    fake_write_row.expect('__call__', ((1,2), [2, 2, 2]), {})
    fake_process_crash.expect('__call__', (3, fake_IdCache), {}, [3, 3, 3])
    fake_write_row.expect('__call__', ((1,2), [3, 3, 3]), {})

    fake_database_pool.expect('cleanup', (), {})

    dailyUrl.dailyUrlDump(conf,
                          sdb=fake_database_module,
                          gzipped_csv_files=fake_gzipped_file_context_manager,
                          IdCache=fake_IdCache,
                          write_row=fake_write_row,
                          process_crash=fake_process_crash,
                          logger=fake_logger)



