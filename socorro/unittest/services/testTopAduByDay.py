# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import socorro.unittest.testlib.expectations as expect
import socorro.services.aduByDay as abd
import socorro.lib.util as util
from socorro.lib.datetimeutil import UTC
from nose.plugins.skip import SkipTest

import datetime as dt

singleQueryReturn1 = [(dt.datetime(2009,12,1,tzinfo=UTC), 'Windows', 1000),
                      (dt.datetime(2009,12,1,tzinfo=UTC), 'Linux', 999),
                      (dt.datetime(2009,12,2,tzinfo=UTC), 'Windows', 900),
                      (dt.datetime(2009,12,2,tzinfo=UTC), 'Linux', 899),
                      (dt.datetime(2009,12,3,tzinfo=UTC), 'Windows', 800),
                      (dt.datetime(2009,12,3,tzinfo=UTC), 'Linux', 799),
                      (dt.datetime(2009,12,4,tzinfo=UTC), 'Windows', 700),
                      (dt.datetime(2009,12,4,tzinfo=UTC), 'Linux', 699),
                      (dt.datetime(2009,12,5,tzinfo=UTC), 'Windows', 600),
                      (dt.datetime(2009,12,5,tzinfo=UTC), 'Linux', 599),
                     ]
singleQueryReturn2 = [(dt.datetime(2009,12,1,tzinfo=UTC), 'Windows', 10),
                      (dt.datetime(2009,12,1,tzinfo=UTC), 'Linux', 11),
                      (dt.datetime(2009,12,2,tzinfo=UTC), 'Windows', 12),
                      (dt.datetime(2009,12,2,tzinfo=UTC), 'Linux', 13),
                      (dt.datetime(2009,12,3,tzinfo=UTC), 'Windows', 14),
                      (dt.datetime(2009,12,3,tzinfo=UTC), 'Linux', 15),
                      (dt.datetime(2009,12,4,tzinfo=UTC), 'Windows', 16),
                      (dt.datetime(2009,12,4,tzinfo=UTC), 'Linux', 17),
                      (dt.datetime(2009,12,5,tzinfo=UTC), 'Windows', 18),
                      (dt.datetime(2009,12,5,tzinfo=UTC), 'Linux', 19),
                     ]
singleQueryReturn3 = [(dt.datetime(2009,12,1,tzinfo=UTC), 'Windows', 10),
                      (dt.datetime(2009,12,1,tzinfo=UTC), 'Linux', 11),
                      (dt.datetime(2009,12,1,tzinfo=UTC), 'Mac', 111),
                      (dt.datetime(2009,12,2,tzinfo=UTC), 'Windows', 12),
                      (dt.datetime(2009,12,2,tzinfo=UTC), 'Linux', 13),
                      (dt.datetime(2009,12,2,tzinfo=UTC), 'Mac', 113),
                      (dt.datetime(2009,12,3,tzinfo=UTC), 'Windows', 14),
                      (dt.datetime(2009,12,3,tzinfo=UTC), 'Linux', 15),
                      (dt.datetime(2009,12,3,tzinfo=UTC), 'Mac', 115),
                      (dt.datetime(2009,12,4,tzinfo=UTC), 'Windows', 16),
                      (dt.datetime(2009,12,4,tzinfo=UTC), 'Linux', 17),
                      (dt.datetime(2009,12,4,tzinfo=UTC), 'Mac', 117),
                      (dt.datetime(2009,12,5,tzinfo=UTC), 'Windows', 18),
                      (dt.datetime(2009,12,5,tzinfo=UTC), 'Linux', 19),
                      (dt.datetime(2009,12,5,tzinfo=UTC), 'Mac', 119),
                     ]
expectedHistory1 = { (dt.datetime(2009,12,1,tzinfo=UTC), 'Windows'): 1000,
                     (dt.datetime(2009,12,1,tzinfo=UTC), 'Linux'): 999,
                     (dt.datetime(2009,12,2,tzinfo=UTC), 'Windows'): 900,
                     (dt.datetime(2009,12,2,tzinfo=UTC), 'Linux'): 899,
                     (dt.datetime(2009,12,3,tzinfo=UTC), 'Windows'): 800,
                     (dt.datetime(2009,12,3,tzinfo=UTC), 'Linux'): 799,
                     (dt.datetime(2009,12,4,tzinfo=UTC), 'Windows'): 700,
                     (dt.datetime(2009,12,4,tzinfo=UTC), 'Linux'): 699,
                     (dt.datetime(2009,12,5,tzinfo=UTC), 'Windows'): 600,
                     (dt.datetime(2009,12,5,tzinfo=UTC), 'Linux'): 599,
                   }
expectedHistory2 = { (dt.datetime(2009,12,1,tzinfo=UTC), 'Windows'): 10,
                     (dt.datetime(2009,12,1,tzinfo=UTC), 'Linux'): 11,
                     (dt.datetime(2009,12,2,tzinfo=UTC), 'Windows'): 12,
                     (dt.datetime(2009,12,2,tzinfo=UTC), 'Linux'): 13,
                     (dt.datetime(2009,12,3,tzinfo=UTC), 'Windows'): 14,
                     (dt.datetime(2009,12,3,tzinfo=UTC), 'Linux'): 15,
                     (dt.datetime(2009,12,4,tzinfo=UTC), 'Windows'): 16,
                     (dt.datetime(2009,12,4,tzinfo=UTC), 'Linux'): 17,
                     (dt.datetime(2009,12,5,tzinfo=UTC), 'Windows'): 18,
                     (dt.datetime(2009,12,5,tzinfo=UTC), 'Linux'): 19,
                  }
expectedHistory3 = { (dt.datetime(2009,12,1,tzinfo=UTC), 'Windows'): 10,
                     (dt.datetime(2009,12,1,tzinfo=UTC), 'Linux'): 11,
                     (dt.datetime(2009,12,1,tzinfo=UTC), 'Mac'): 111,
                     (dt.datetime(2009,12,2,tzinfo=UTC), 'Windows'): 12,
                     (dt.datetime(2009,12,2,tzinfo=UTC), 'Linux'): 13,
                     (dt.datetime(2009,12,2,tzinfo=UTC), 'Mac'): 113,
                     (dt.datetime(2009,12,3,tzinfo=UTC), 'Windows'): 14,
                     (dt.datetime(2009,12,3,tzinfo=UTC), 'Linux'): 15,
                     (dt.datetime(2009,12,3,tzinfo=UTC), 'Mac'): 115,
                     (dt.datetime(2009,12,4,tzinfo=UTC), 'Windows'): 16,
                     (dt.datetime(2009,12,4,tzinfo=UTC), 'Linux'): 17,
                     (dt.datetime(2009,12,4,tzinfo=UTC), 'Mac'): 117,
                     (dt.datetime(2009,12,5,tzinfo=UTC), 'Windows'): 18,
                     (dt.datetime(2009,12,5,tzinfo=UTC), 'Linux'): 19,
                     (dt.datetime(2009,12,5,tzinfo=UTC), 'Mac'): 119,
                  }
combineAduCrashHistoryResult = [
                     util.DotDict({'date': '2009-12-01',
                                   'os': 'Linux',
                                   'users': 999,
                                   'crashes': 11}),
                     util.DotDict({'date': '2009-12-01',
                                   'os': 'Windows',
                                   'users': 1000,
                                   'crashes': 10}),
                     util.DotDict({'date': '2009-12-02',
                                   'os': 'Linux',
                                   'users': 899,
                                   'crashes': 13}),
                     util.DotDict({'date': '2009-12-02',
                                   'os': 'Windows',
                                   'users': 900,
                                   'crashes': 12}),
                     util.DotDict({'date': '2009-12-03',
                                   'os': 'Linux',
                                   'users': 799,
                                   'crashes': 15}),
                     util.DotDict({'date': '2009-12-03',
                                   'os': 'Windows',
                                   'users': 800,
                                   'crashes': 14}),
                     util.DotDict({'date': '2009-12-04',
                                   'os': 'Linux',
                                   'users': 699,
                                   'crashes': 17}),
                     util.DotDict({'date': '2009-12-04',
                                   'os': 'Windows',
                                   'users': 700,
                                   'crashes': 16}),
                     util.DotDict({'date': '2009-12-05',
                                   'os': 'Linux',
                                   'users': 599,
                                   'crashes': 19}),
                     util.DotDict({'date': '2009-12-05',
                                   'os': 'Windows',
                                   'users': 600,
                                   'crashes': 18}),
                   ]
#-----------------------------------------------------------------------------------------------------------------
def getDummyContext():
  context = util.DotDict()
  context.databaseHost = 'fred'
  context.databaseName = 'wilma'
  context.databaseUserName = 'ricky'
  context.databasePassword = 'lucy'
  context.databasePort = 127
  return context

#-----------------------------------------------------------------------------------------------------------------
def testAduByDay_semicolonStringToListSanitized():
  assert abd.semicolonStringToListSanitized("aa;bb;cc") == ['aa', 'bb', 'cc']
  assert abd.semicolonStringToListSanitized(" aa  ;bb;cc  ") == ['aa', 'bb', 'cc']
  assert abd.semicolonStringToListSanitized("aa;'; delete * from reports; --bb;  cc") == ['aa', 'delete * from reports', '--bb', 'cc']

#-----------------------------------------------------------------------------------------------------------------
def testAduByDay__init__():
  context = getDummyContext()
  adu = abd.AduByDay(context)
  assert adu.context == context

#-----------------------------------------------------------------------------------------------------------------
def testAduByDay_get1():
  raise SkipTest("FIXME")
  context = getDummyContext()
  context.productVersionCache = expect.DummyObjectWithExpectations('dummyProductVersionCache')
  context.productVersionCache.expect('getId', ('Firefox', '3.5.5'), {}, 149)
  dummyConnection = expect.DummyObjectWithExpectations('dummyConnection')
  dummyConnection.expect('close', (), {}, None)
  dummyDatabase = expect.DummyObjectWithExpectations('dummyDatabase')
  dummyDatabase.expect('connection', (), {}, dummyConnection)
  class AduByDay2(abd.AduByDay):
    def __init__(self, parameters):
      super(AduByDay2, self).__init__(parameters)
    def aduByDay(self, parameters):
      return parameters
  adu = AduByDay2(context)
  adu.database = dummyDatabase

  result = adu.get('Firefox', '3.5.5', 'Windows', '2009-12-15', '2009-12-31')

  expectedResult = { 'product': 'Firefox',
                     'listOfVersions': [ '3.5.5' ],
                     'listOfOs_names': [ 'Windows'],
                     'start_date': dt.datetime(2009, 12, 15,tzinfo=UTC),
                     'end_date': dt.datetime(2009, 12, 31,tzinfo=UTC),
                     'productdims_idList': [ 149 ],
                   }

  assert result == expectedResult, "expected %s, but got %s" % (expectedResult, result)

#-----------------------------------------------------------------------------------------------------------------
def testAduByDay_get2():
  raise SkipTest("FIXME")
  context = getDummyContext()
  context.productVersionCache = expect.DummyObjectWithExpectations('dummyProductVersionCache')
  context.productVersionCache.expect('getId', ('Firefox', '3.5.5'), {}, 149)
  context.productVersionCache.expect('getId', ('Firefox', '3.5.4'), {}, 666)
  dummyConnection = expect.DummyObjectWithExpectations('dummyConnection')
  dummyConnection.expect('close', (), {}, None)
  dummyDatabase = expect.DummyObjectWithExpectations('dummyDatabase')
  dummyDatabase.expect('connection', (), {}, dummyConnection)
  class AduByDay2(abd.AduByDay):
    def __init__(self, parameters):
      super(AduByDay2, self).__init__(parameters)
    def aduByDay(self, parameters):
      return parameters
  adu = AduByDay2(context)
  adu.database = dummyDatabase

  result = adu.get('Firefox', '3.5.5;3.5.4', 'Windows;Linux', '2009-12-15', '2009-12-31')

  expectedResult = { 'product': 'Firefox',
                     'listOfVersions': [ '3.5.5', '3.5.4' ],
                     'listOfOs_names': [ 'Windows', 'Linux'],
                     'start_date': dt.datetime(2009, 12, 15,tzinfo=UTC),
                     'end_date': dt.datetime(2009, 12, 31,tzinfo=UTC),
                     'productdims_idList': [ 149, 666 ],
                   }

  assert result == expectedResult, "expected %s, but got %s" % (expectedResult, result)

#-----------------------------------------------------------------------------------------------------------------
def testAduByDay_get3():
  raise SkipTest("FIXME")
  context = getDummyContext()
  context.productVersionCache = expect.DummyObjectWithExpectations('dummyProductVersionCache')
  context.productVersionCache.expect('getId', ('Firefox', '3.5.5'), {}, 149)
  context.productVersionCache.expect('getId', ('Firefox', '3.5.4'), {}, 666)
  dummyConnection = expect.DummyObjectWithExpectations('dummyConnection')
  dummyConnection.expect('close', (), {}, None)
  dummyDatabase = expect.DummyObjectWithExpectations('dummyDatabase')
  dummyDatabase.expect('connection', (), {}, dummyConnection)
  class AduByDay2(abd.AduByDay):
    def __init__(self, parameters):
      super(AduByDay2, self).__init__(parameters)
    def aduByDay(self, parameters):
      return parameters
  adu = AduByDay2(context)
  adu.database = dummyDatabase

  result = adu.get('Firefox', '3.5.5;   3.5.4', '    Windows;   Linux', '2009-12-15', '2009-12-31')

  expectedResult = { 'product': 'Firefox',
                     'listOfVersions': [ '3.5.5', '3.5.4' ],
                     'listOfOs_names': [ 'Windows', 'Linux'],
                     'start_date': dt.datetime(2009, 12, 15,tzinfo=UTC),
                     'end_date': dt.datetime(2009, 12, 31,tzinfo=UTC),
                     'productdims_idList': [ 149, 666 ],
                   }

  assert result == expectedResult, "expected %s, but got %s" % (expectedResult, result)

#-----------------------------------------------------------------------------------------------------------------
def testAduByDay_fetchAduHistory1():
  raise SkipTest("FIXME")
  parameters = util.DotDict({ 'start_date': dt.datetime(2009, 12, 1,tzinfo=UTC),
                              'end_date': dt.datetime(2009, 12, 15,tzinfo=UTC),
                              'product': 'Firefox',
                              'version': '3.5.5',
                              'listOfOs_names': ['Windows', 'Mac'],
                           })
  sql = """
      select
          date,
          case when product_os_platform = 'Mac OS/X' then
            'Mac'
          else
            product_os_platform
          end as product_os_platform,
          sum(adu_count)
      from
          raw_adu ra
      where
          %(start_date)s <= date
          and date <= %(end_date)s
          and product_name = %(product)s
          and product_version = %(version)s
          and product_os_platform in ('Windows','Mac OS/X')
      group by
          date,
          product_os_platform
      order by
          1"""
  sqlReturn = singleQueryReturn1
  dummyCursor = expect.DummyObjectWithExpectations('dummyCursor')
  #dummyCursor.expect('tobecalled', args, kwargs, retvalue)
  dummyCursor.expect('execute', (sql, parameters), {}, sqlReturn)
  for x in sqlReturn:
    dummyCursor.expect('fetchone', (), {}, x)
  dummyCursor.expect('fetchone', (), {}, None, StopIteration)
  dummyConnection = expect.DummyObjectWithExpectations('dummyConnection')
  dummyConnection.expect('cursor', (), {}, dummyCursor)
  context = getDummyContext()
  adu = abd.AduByDay(context)
  adu.connection = dummyConnection

  result = adu.fetchAduHistory(parameters)

  expectedResult = expectedHistory1
  assert result == expectedResult, "expected %s, but got %s" % (expectedResult, result)

#-----------------------------------------------------------------------------------------------------------------
def testAduByDay_fetchAduHistory2():
  raise SkipTest("FIXME")
  parameters = util.DotDict({ 'start_date': dt.datetime(2009, 12, 1,tzinfo=UTC),
                              'end_date': dt.datetime(2009, 12, 15,tzinfo=UTC),
                              'product': 'Firefox',
                              'version': '3.5.5',
                              'listOfOs_names': [''],
                           })
  # the odd literal \n in the string below is to prevent the Wing Python IDE from eliminating
  # trailing whitespace at the end of the line before the "group by" clause.
  sql = """
      select
          date,
          case when product_os_platform = 'Mac OS/X' then
            'Mac'
          else
            product_os_platform
          end as product_os_platform,
          sum(adu_count)
      from
          raw_adu ra
      where
          %(start_date)s <= date
          and date <= %(end_date)s
          and product_name = %(product)s
          and product_version = %(version)s
          \n      group by
          date,
          product_os_platform
      order by
          1"""
  sqlReturn = singleQueryReturn3
  dummyCursor = expect.DummyObjectWithExpectations('dummyCursor')
  #dummyCursor.expect('tobecalled', args, kwargs, retvalue)
  dummyCursor.expect('execute', (sql, parameters), {}, sqlReturn)
  for x in sqlReturn:
    dummyCursor.expect('fetchone', (), {}, x)
  dummyCursor.expect('fetchone', (), {}, None, StopIteration)
  dummyConnection = expect.DummyObjectWithExpectations('dummyConnection')
  dummyConnection.expect('cursor', (), {}, dummyCursor)
  context = getDummyContext()
  adu = abd.AduByDay(context)
  adu.connection = dummyConnection

  result = adu.fetchAduHistory(parameters)

  expectedResult = expectedHistory3
  assert result == expectedResult, "expected %s, but got %s" % (expectedResult, result)

#-----------------------------------------------------------------------------------------------------------------
def testAduByDay_fetchCrashHistory():
  raise SkipTest("FIXME")
  parameters = util.DotDict({ 'start_date': dt.datetime(2009, 12, 1,tzinfo=UTC),
                              'end_date': dt.datetime(2009, 12, 15,tzinfo=UTC),
                              'product': 'Firefox',
                              'version': '3.5.5',
                              'listOfOs_names': ['Windows', 'Mac'],
                              'socorroTimeToUTCInterval':'8 hours',
                              'productdims_id':171,
                           })
  sql = """
      select
          CAST(ceil(EXTRACT(EPOCH FROM (window_end - timestamp with time zone %(start_date)s - interval %(socorroTimeToUTCInterval)s)) / 86400) AS INT) * interval '24 hours' + timestamp with time zone %(start_date)s as day,
          case when os.os_name = 'Windows NT' then
            'Windows'
          when os.os_name = 'Mac OS X' then
            'Mac'
          else
            os.os_name
          end as os_name,
          sum(count)
      from
          top_crashes_by_signature tcbs
              join osdims os on tcbs.osdims_id = os.id
                  and os.os_name in ('Windows','Mac OS X','Windows NT')
      where
          (timestamp with time zone %(start_date)s - interval %(socorroTimeToUTCInterval)s) < window_end
          and window_end <= (timestamp with time zone %(end_date)s - interval %(socorroTimeToUTCInterval)s)
          and productdims_id = %(productdims_id)s
      group by
          1, 2
      order by
          1, 2"""
  sqlReturn = singleQueryReturn1
  dummyCursor = expect.DummyObjectWithExpectations('dummyCursor')
  #dummyCursor.expect('tobecalled', args, kwargs, retvalue)
  dummyCursor.expect('execute', (sql, parameters), {}, sqlReturn)
  for x in sqlReturn:
    dummyCursor.expect('fetchone', (), {}, x)
  dummyCursor.expect('fetchone', (), {}, None, StopIteration)
  dummyConnection = expect.DummyObjectWithExpectations('dummyConnection')
  dummyConnection.expect('cursor', (), {}, dummyCursor)
  context = getDummyContext()
  adu = abd.AduByDay(context)
  adu.connection = dummyConnection

  result = adu.fetchCrashHistory(parameters)

  expectedResult = expectedHistory1
  assert result == expectedResult, "expected %s, but got %s" % (expectedResult, result)

#-----------------------------------------------------------------------------------------------------------------
def testAduByDay_combineAduCrashHistory():
  context = getDummyContext()
  adu = abd.AduByDay(context)

  expectedResult = combineAduCrashHistoryResult
  result = adu.combineAduCrashHistory(expectedHistory1, expectedHistory2)
  assert result == expectedResult, "expected %s, but got %s" % (expectedResult, result)


#-----------------------------------------------------------------------------------------------------------------
def testAduByDay_aduByDay1():
  context = getDummyContext()
  class AduByDay3(abd.AduByDay):
    def __init__(self, parameters):
      super(AduByDay3, self).__init__(parameters)
    def fetchAduHistory(self, parameters):
      return expectedHistory1
    def fetchCrashHistory(self, parameters):
      return expectedHistory2
    #def combineAduCrashHistory(self, aduHistory, crashHistory):
      #return combineAduCrashHistoryResult
  adu = AduByDay3(context)

  parameters = util.DotDict({ 'product': 'Firefox',
                              'listOfVersions': [ '3.5.5' ],
                              'listOfOs_names': [ 'Windows', 'Linux'],
                              'start_date': dt.datetime(2009, 12, 15,tzinfo=UTC),
                              'end_date': dt.datetime(2009, 12, 31,tzinfo=UTC),
                              'productdims_idList': [ 149 ],
                           })

  result = adu.aduByDay(parameters)

  expectedResult = { 'product': parameters.product,
                     'start_date': str(parameters.start_date),
                     'end_date': str(parameters.end_date),
                     'versions': [ { 'version': '3.5.5',
                                     'statistics': combineAduCrashHistoryResult
                                 } ]
                   }
  assert result == expectedResult, "expected %s, but got %s" % (expectedResult, result)

  #-----------------------------------------------------------------------------------------------------------------
def testAduByDay_aduByDay2():
  context = getDummyContext()
  class AduByDay3(abd.AduByDay):
    def __init__(self, parameters):
      super(AduByDay3, self).__init__(parameters)
    def fetchAduHistory(self, parameters):
      return expectedHistory1
    def fetchCrashHistory(self, parameters):
      return expectedHistory2
    #def combineAduCrashHistory(self, aduHistory, crashHistory):
      #return combineAduCrashHistoryResult
  adu = AduByDay3(context)

  parameters = util.DotDict({ 'product': 'Firefox',
                              'listOfVersions': [ '3.5.5', '3.5.4' ],
                              'listOfOs_names': [ 'Windows', 'Linux'],
                              'start_date': dt.datetime(2009, 12, 15,tzinfo=UTC),
                              'end_date': dt.datetime(2009, 12, 31,tzinfo=UTC),
                              'productdims_idList': [ 149, 666 ],
                           })

  result = adu.aduByDay(parameters)

  expectedResult = { 'product': parameters.product,
                     'start_date': str(parameters.start_date),
                     'end_date': str(parameters.end_date),
                     'versions': [ { 'version': '3.5.5',
                                     'statistics': combineAduCrashHistoryResult
                                   },
                                   { 'version': '3.5.4',
                                     'statistics': combineAduCrashHistoryResult
                                   },
                                 ]
                   }
  assert result == expectedResult, "expected %s, but got %s" % (expectedResult, result)
