import socorro.unittest.testlib.expectations as expect
import socorro.services.topCrashBySignatureTrends as tcbst
import socorro.lib.util as util

import datetime as dt

import nose.tools as nt


class DotDict(dict):
  __getattr__= dict.__getitem__
  __setattr__= dict.__setitem__
  __delattr__= dict.__delitem__

def dummyQueryExecutionFunction(ignoredCursor, inputParameters):
  return inputParameters

def dummyQueryExecutionFunctionReturningQueryParametersGenerator1(ignoredCursor, ignoredParameters):
  columnNames = ['signature', 'count', 'percentOfTotal', 'win', 'mac', 'linux']
  values = [('sig1', 10, 0.01,10,0,0), ('sig2', 5, 0.005,5,0,0), ('sig3', 1, 0.001,0,1,0)]
  return (dict(zip(columnNames, x)) for x in values)

#-----------------------------------------------------------------------------------------------------------------
def testTotalNumberOfCrashesForPeriod ():
  dummyCursor = expect.DummyObjectWithExpectations()
  #dummyCursor.expect('tobecalled', args, kwargs, retvalue)
  parameters = {}
  sql = """
    select
        sum(tcbs.count)
    from
        top_crashes_by_signature tcbs
    where
        %(startDate)s < tcbs.window_end
        and tcbs.window_end <= %(endDate)s
        and tcbs.productdims_id = %(productdims_id)s
    """
  dummyCursor.expect('execute', (sql, parameters), {}, None)
  dummyCursor.expect('fetchall', (), {}, [(22,)])
  result = tcbst.totalNumberOfCrashesForPeriod(dummyCursor,parameters)
  assert result == 22, 'expected to get 22, but got %s instead' % result

#-----------------------------------------------------------------------------------------------------------------
def testGetListOfTopCrashersBySignature ():
  dummyCursor = expect.DummyObjectWithExpectations()
  #dummyCursor.expect('tobecalled', args, kwargs, retvalue)
  parameters = {}
  sql = """
  select
      tcbs.signature,
      sum(tcbs.count) as count,
      cast(sum(tcbs.count) as float) / %(totalNumberOfCrashes)s as percentOfTotal,
      sum(case when os.os_name LIKE 'Windows%%' then tcbs.count else 0 end) as win_count,
      sum(case when os.os_name = 'Mac OS X' then tcbs.count else 0 end) as mac_count,
      sum(case when os.os_name = 'Linux' then tcbs.count else 0 end) as linux_count
  from
      top_crashes_by_signature tcbs
          join osdims os on tcbs.osdims_id = os.id
                            and %(startDate)s < tcbs.window_end
                            and tcbs.window_end <= %(endDate)s
                            and tcbs.productdims_id = %(productdims_id)s
  group by
      tcbs.signature
  order by
    2 desc
  limit %(listSize)s"""
  expectedResult =  [('sig1', 10, 0.01,10,0,0), ('sig2', 5, 0.005,5,0,0), ('sig3', 1, 0.001,0,1,0)]
  dummyCursor.expect('execute', (sql, parameters), {}, None)
  for singleResult in expectedResult:
    dummyCursor.expect('fetchone', (), {}, singleResult)
  dummyCursor.expect('fetchone', (), {}, None)
  def dummyTotalNumberOfCrashesForPeriod(*args):
    return 15
  result = tcbst.getListOfTopCrashersBySignature(dummyCursor,parameters,dummyTotalNumberOfCrashesForPeriod)
  for x, y in zip (result, expectedResult):
    assert x == y, 'expected to get %s, but got %s instead' % (x, y)

#----------------------------------------------------------------------------------------------------------------
def testRangeOfQueriesGenerator1():
  d = DotDict()
  try:
    for q in tcbst.rangeOfQueriesGenerator(None, d, dummyQueryExecutionFunction):
      pass
  except KeyError:
    pass
  else:
    raise Exception("the generator should have raised a KeyError")

#----------------------------------------------------------------------------------------------------------------
def testRangeOfQueriesGenerator2():
  d = DotDict()
  d.logger = util.FakeLogger()
  d.product = None
  d.version = None
  d.os_name = None
  d.os_version = None
  d.startDate = None
  d.endDate = None
  d.duration = None
  result = [x for x in tcbst.rangeOfQueriesGenerator(None, d, dummyQueryExecutionFunction)]
  assert len(result) == 0, "it shouldn't have returned anything"

#----------------------------------------------------------------------------------------------------------------
def testRangeOfQueriesGenerator3():
  d = DotDict()
  d.logger = util.SilentFakeLogger()
  d.startDate = dt.datetime(2009, 10, 21)
  d.endDate = dt.datetime(2009, 10, 22)
  d.duration = dt.timedelta(days=1)
  expectedResult = [{'startDate': dt.datetime(2009, 10, 21, 0, 0),
                     'endDate': dt.datetime(2009, 10, 22, 0, 0),
                     'duration': dt.timedelta(1),
                     'logger': d.logger},
                   ]
  result = [x for x in tcbst.rangeOfQueriesGenerator(None, d, dummyQueryExecutionFunction)]
  assert len(result) == 1, "it should have returned only one item, but it gave back %d" % len(result)
  for actual, expected in zip(result, expectedResult):
    assert actual == expected, "expected %s, but got %s" % (expected, actual)


#----------------------------------------------------------------------------------------------------------------
def testRangeOfQueriesGenerator4():
  d = DotDict()
  d.logger = util.SilentFakeLogger()
  d.startDate = dt.datetime(2009, 10, 21)
  d.endDate = dt.datetime(2009, 10, 23)
  d.duration = dt.timedelta(days=1)
  expectedResult = [{'startDate': dt.datetime(2009, 10, 21, 0, 0),
                     'endDate': dt.datetime(2009, 10, 22, 0, 0),
                     'duration': dt.timedelta(1),
                     'logger': d.logger},
                    {'startDate': dt.datetime(2009, 10, 22, 0, 0),
                     'endDate': dt.datetime(2009, 10, 23, 0, 0),
                     'duration': dt.timedelta(1),
                     'logger': d.logger},
                   ]
  result = [x for x in tcbst.rangeOfQueriesGenerator(None, d, dummyQueryExecutionFunction)]
  print result
  assert len(result) == 2, "it should have returned two items, but it gave back %d" % len(result)
  for actual, expected in zip(result, expectedResult):
    assert actual == expected, "expected %s, but got %s" % (expected, actual)

#----------------------------------------------------------------------------------------------------------------
def testRangeOfQueriesGenerator5():
  d = DotDict()
  d.logger = util.SilentFakeLogger()
  d.product = 'Firefox'
  d.version = '3.5.6'
  d.os_name = 'Linux'
  d.os_version = '2.6.3'
  d.startDate = dt.datetime(2009, 10, 19)
  d.endDate = dt.datetime(2009, 10, 22)
  d.duration = dt.timedelta(days=1)
  #should return a list of three generators
  result = [x for x in tcbst.rangeOfQueriesGenerator(None, d, dummyQueryExecutionFunctionReturningQueryParametersGenerator1)]
  assert len(result) == 3, "it should have returned only three item, but it gave back %d" % len(result)
  #this test is really a tautology since all the generators here are really the same one
  for aGen in result:
    for actual, expected in zip(aGen, (x for x in dummyQueryExecutionFunctionReturningQueryParametersGenerator1(1,2))):
      assert actual == expected, "expected %s, but got %s" % (expected, actual)

#----------------------------------------------------------------------------------------------------------------
def testListOfListsWithChangeInRank01():
  listOfLists = [[
                   ('s1', 100, 10.0, 100,  0,  0),
                   ('s2',  90,  9.0,  80,  5,  5),
                   ('s3',  80,  8.0,  60, 20,  0),
                 ],
                 [
                   ('s1', 100, 10.0, 100,  0,  0),
                   ('s2',  90,  9.0,  80,  5,  5),
                   ('s3',  80,  8.0,  60, 20,  0),
                 ]
                ]
  expectedResult = [
                     {'signature': 's1', 'count': 100, 'percentOfTotal': 10.0, 'win_count': 100, 'mac_count':  0, 'linux_count': 0, 'currentRank': 0, 'previousRank': 0, 'previousPercentOfTotal': 10.0, 'changeInRank': 0, 'changeInPercentOfTotal': 0.0},
                     {'signature': 's2', 'count':  90, 'percentOfTotal':  9.0, 'win_count':  80, 'mac_count':  5, 'linux_count': 5, 'currentRank': 1, 'previousRank': 1, 'previousPercentOfTotal':  9.0, 'changeInRank': 0, 'changeInPercentOfTotal': 0.0},
                     {'signature': 's3', 'count':  80, 'percentOfTotal':  8.0, 'win_count':  60, 'mac_count': 20, 'linux_count': 0, 'currentRank': 2, 'previousRank': 2, 'previousPercentOfTotal':  8.0, 'changeInRank': 0, 'changeInPercentOfTotal': 0.0},
                   ]
  result = tcbst.listOfListsWithChangeInRank(listOfLists)
  assert type(result) == list
  assert type(result[0]) == list
  for x,y in zip(result[0], expectedResult):
    assert x == y

#----------------------------------------------------------------------------------------------------------------
def testListOfListsWithChangeInRank02():
  listOfLists = [[
                   ('s1', 100, 10.0, 100,  0,  0),
                   ('s2',  90,  9.0,  80,  5,  5),
                   ('s3',  80,  8.0,  60, 20,  0),
                 ],
                 [
                   ('s2', 100, 10.0, 100,  0,  0),
                   ('s1',  90,  9.0,  80,  5,  5),
                   ('s3',  80,  8.0,  60, 20,  0),
                 ]
                ]
  expectedResult = [
                     {'signature': 's2', 'count': 100, 'percentOfTotal': 10.0, 'win_count': 100, 'mac_count':  0, 'linux_count': 0, 'currentRank': 0, 'previousRank': 1, 'previousPercentOfTotal':  9.0, 'changeInRank':  1, 'changeInPercentOfTotal':  1.0},
                     {'signature': 's1', 'count':  90, 'percentOfTotal':  9.0, 'win_count':  80, 'mac_count':  5, 'linux_count': 5, 'currentRank': 1, 'previousRank': 0, 'previousPercentOfTotal': 10.0, 'changeInRank': -1, 'changeInPercentOfTotal': -1.0},
                     {'signature': 's3', 'count':  80, 'percentOfTotal':  8.0, 'win_count':  60, 'mac_count': 20, 'linux_count': 0, 'currentRank': 2, 'previousRank': 2, 'previousPercentOfTotal':  8.0, 'changeInRank':  0, 'changeInPercentOfTotal':  0.0},
                   ]
  result = tcbst.listOfListsWithChangeInRank(listOfLists)
  assert type(result) == list
  assert type(result[0]) == list
  for x,y in zip(result[0], expectedResult):
    assert x == y

#----------------------------------------------------------------------------------------------------------------
def testListOfListsWithChangeInRank03():
  listOfLists = [[
                   ('s1', 100, 10.0, 100,  0,  0),
                   ('s2',  90,  9.0,  80,  5,  5),
                   ('s3',  80,  8.0,  60, 20,  0),
                 ],
                 [
                   ('s2', 100, 10.0, 100,  0,  0),
                   ('s1',  90,  9.0,  80,  5,  5),
                   ('s3',  80,  8.0,  60, 20,  0),
                 ],
                 [
                   ('s3', 100, 10.0, 100,  0,  0),
                   ('s1',  90,  9.0,  80,  5,  5),
                   ('s2',  80,  8.0,  60, 20,  0),
                 ],
                ]
  expectedResult0 = [
                     {'signature': 's2', 'count': 100, 'percentOfTotal': 10.0, 'win_count': 100, 'mac_count':  0, 'linux_count': 0, 'currentRank': 0, 'previousRank': 1, 'previousPercentOfTotal':  9.0, 'changeInRank':  1, 'changeInPercentOfTotal':  1.0},
                     {'signature': 's1', 'count':  90, 'percentOfTotal':  9.0, 'win_count':  80, 'mac_count':  5, 'linux_count': 5, 'currentRank': 1, 'previousRank': 0, 'previousPercentOfTotal': 10.0, 'changeInRank': -1, 'changeInPercentOfTotal': -1.0},
                     {'signature': 's3', 'count':  80, 'percentOfTotal':  8.0, 'win_count':  60, 'mac_count': 20, 'linux_count': 0, 'currentRank': 2, 'previousRank': 2, 'previousPercentOfTotal':  8.0, 'changeInRank':  0, 'changeInPercentOfTotal':  0.0},
                   ]
  expectedResult1 = [
                     {'signature': 's3', 'count': 100, 'percentOfTotal': 10.0, 'win_count': 100, 'mac_count':  0, 'linux_count': 0, 'currentRank': 0, 'previousRank': 2, 'previousPercentOfTotal':  8.0, 'changeInRank':  2, 'changeInPercentOfTotal':  2.0},
                     {'signature': 's1', 'count':  90, 'percentOfTotal':  9.0, 'win_count':  80, 'mac_count':  5, 'linux_count': 5, 'currentRank': 1, 'previousRank': 1, 'previousPercentOfTotal':  9.0, 'changeInRank':  0, 'changeInPercentOfTotal':  0.0},
                     {'signature': 's2', 'count':  80, 'percentOfTotal':  8.0, 'win_count':  60, 'mac_count': 20, 'linux_count': 0, 'currentRank': 2, 'previousRank': 0, 'previousPercentOfTotal': 10.0, 'changeInRank': -2, 'changeInPercentOfTotal': -2.0},
                   ]
  result = tcbst.listOfListsWithChangeInRank(listOfLists)
  assert type(result) == list
  assert type(result[0]) == list
  for x,y in zip(result[0], expectedResult0):
    assert x == y
  for x,y in zip(result[1], expectedResult1):
    assert x == y

#----------------------------------------------------------------------------------------------------------------
def testListOfListsWithChangeInRank04():
  listOfLists = [[
                   ('s1', 100, 10.0, 100,  0,  0),
                   ('s2',  90,  9.0,  80,  5,  5),
                   ('s3',  80,  8.0,  60, 20,  0),
                 ],
                 [
                   ('s2', 100, 10.0, 100,  0,  0),
                   ('s1',  90,  9.0,  80,  5,  5),
                   ('s3',  80,  8.0,  60, 20,  0),
                 ],
                 [
                   ('s3', 100, 10.0, 100,  0,  0),
                   ('s1',  90,  9.0,  80,  5,  5),
                   ('s4',  80,  8.0,  60, 20,  0),
                 ],
                ]
  expectedResult0 = [
                     {'signature': 's2', 'count': 100, 'percentOfTotal': 10.0, 'win_count': 100, 'mac_count':  0, 'linux_count': 0, 'currentRank': 0, 'previousRank': 1, 'previousPercentOfTotal':  9.0, 'changeInRank':  1, 'changeInPercentOfTotal':  1.0},
                     {'signature': 's1', 'count':  90, 'percentOfTotal':  9.0, 'win_count':  80, 'mac_count':  5, 'linux_count': 5, 'currentRank': 1, 'previousRank': 0, 'previousPercentOfTotal': 10.0, 'changeInRank': -1, 'changeInPercentOfTotal': -1.0},
                     {'signature': 's3', 'count':  80, 'percentOfTotal':  8.0, 'win_count':  60, 'mac_count': 20, 'linux_count': 0, 'currentRank': 2, 'previousRank': 2, 'previousPercentOfTotal':  8.0, 'changeInRank':  0, 'changeInPercentOfTotal':  0.0},
                   ]
  expectedResult1 = [
                     {'signature': 's3', 'count': 100, 'percentOfTotal': 10.0, 'win_count': 100, 'mac_count':  0, 'linux_count': 0, 'currentRank': 0, 'previousRank':      2, 'previousPercentOfTotal':    8.0, 'changeInRank':     2, 'changeInPercentOfTotal':   2.0},
                     {'signature': 's1', 'count':  90, 'percentOfTotal':  9.0, 'win_count':  80, 'mac_count':  5, 'linux_count': 5, 'currentRank': 1, 'previousRank':      1, 'previousPercentOfTotal':    9.0, 'changeInRank':     0, 'changeInPercentOfTotal':   0.0},
                     {'signature': 's4', 'count':  80, 'percentOfTotal':  8.0, 'win_count':  60, 'mac_count': 20, 'linux_count': 0, 'currentRank': 2, 'previousRank': "null", 'previousPercentOfTotal': "null", 'changeInRank': "new", 'changeInPercentOfTotal': "new"},
                   ]
  result = tcbst.listOfListsWithChangeInRank(listOfLists)
  assert type(result) == list
  assert type(result[0]) == list
  for x,y in zip(result[0], expectedResult0):
    assert x == y
  for x,y in zip(result[1], expectedResult1):
    assert x == y, "expected %s, but got %s" % (y, x)

#-----------------------------------------------------------------------------------------------------------------
def testLatestEntryBeforeOrEqualTo():
  dummyCursor = expect.DummyObjectWithExpectations()
  aDate = dt.datetime(2009,11,9,8)
  productdims_id = 149
  sql = """
    select
        max(window_end)
    from
        top_crashes_by_signature tcbs
    where
        tcbs.window_end <= %s
        and tcbs.productdims_id = %s
    """
  dummyCursor.expect('execute', (sql, (aDate, 149)), {}, None)
  dummyCursor.expect('fetchall', (), {}, [(dt.datetime(2009,11,9,8),)])
  result = tcbst.latestEntryBeforeOrEqualTo(dummyCursor,aDate, productdims_id)
  assert result == dt.datetime(2009,11,9,8), 'expected to get dt.datetime(2009,11,9,8), but got %s instead' % result

#-----------------------------------------------------------------------------------------------------------------
def testTwoPeriodTopCrasherComparison():
  dummyCursor = expect.DummyObjectWithExpectations()
  context = DotDict()
  context.logger = util.SilentFakeLogger()
  context.endDate = dt.datetime(2009,11,2,10)
  context.duration = dt.timedelta(hours=24)
  context.productdims_id = 149
  context.product = 'Firefox'
  context.version = '3.5.5'
  context.listSize = 3
  dummyProductVersionCache = expect.DummyObjectWithExpectations()
  dummyProductVersionCache.expect('getId', (context.product, context.version), {}, 149)
  context.productVersionCache = dummyProductVersionCache
  def closestEndDate(dummyCursor, endDate, productdims_id):
    assert endDate == context.endDate, "In the call to 'closestEndDate', endDate was expected to be %s, but got %s instead" % (str(context.endDate), str(endDate))
    assert productdims_id == 149, "In the call to 'closestEndDate', productdims_id was expected to be 149, but got %d instead" % productdims_id
    return endDate - dt.timedelta(hours=1)
  queryResults = { dt.datetime(2009,11,1,9):
                     [
                       ('s1', 100, 10.0, 100,  0,  0),
                       ('s2',  90,  9.0,  80,  5,  5),
                       ('s3',  80,  8.0,  60, 20,  0),
                     ],
                  dt.datetime(2009,11,2,9):
                     [
                       ('s2', 100, 10.0, 100,  0,  0),
                       ('s1',  90,  9.0,  80,  5,  5),
                       ('s3',  80,  8.0,  60, 20,  0),
                     ],
                 }
  def listOfTopCrashers(dummyCursor, databaseParameters):
    return queryResults[databaseParameters['endDate']]
  expectedResult = {
    'crashes': [
                 {'signature': 's2', 'count': 100, 'percentOfTotal': 10.0, 'win_count': 100, 'mac_count':  0, 'linux_count': 0, 'currentRank': 0, 'previousRank': 1, 'previousPercentOfTotal':  9.0, 'changeInRank':  1, 'changeInPercentOfTotal':  1.0},
                 {'signature': 's1', 'count':  90, 'percentOfTotal':  9.0, 'win_count':  80, 'mac_count':  5, 'linux_count': 5, 'currentRank': 1, 'previousRank': 0, 'previousPercentOfTotal': 10.0, 'changeInRank': -1, 'changeInPercentOfTotal': -1.0},
                 {'signature': 's3', 'count':  80, 'percentOfTotal':  8.0, 'win_count':  60, 'mac_count': 20, 'linux_count': 0, 'currentRank': 2, 'previousRank': 2, 'previousPercentOfTotal':  8.0, 'changeInRank':  0, 'changeInPercentOfTotal':  0.0},
               ],
    'start_date': str(dt.datetime(2009,11,1,9)),
    'end_date': str(dt.datetime(2009,11,2,9)),
    'totalNumberOfCrashes': 270,
    'totalPercentage': 27.0
    }
  result = tcbst.twoPeriodTopCrasherComparison(dummyCursor, context, closestEndDate, listOfTopCrashers)
  assert result == expectedResult, 'expected %s, but got %s' % (expectedResult, result)

#-----------------------------------------------------------------------------------------------------------------
def testDictList():
  iterable = [
               {'signature': 's2', 'count': 100, 'percentOfTotal': 10.0, 'win_count': 100, 'mac_count':  0, 'linux_count': 0, 'currentRank': 0, 'previousRank': 1, 'previousPercentOfTotal':  9.0, 'changeInRank':  1, 'changeInPercentOfTotal':  1.0},
               {'signature': 's1', 'count':  90, 'percentOfTotal':  9.0, 'win_count':  80, 'mac_count':  5, 'linux_count': 5, 'currentRank': 1, 'previousRank': 0, 'previousPercentOfTotal': 10.0, 'changeInRank': -1, 'changeInPercentOfTotal': -1.0},
               {'signature': 's3', 'count':  80, 'percentOfTotal':  8.0, 'win_count':  60, 'mac_count': 20, 'linux_count': 0, 'currentRank': 2, 'previousRank': 2, 'previousPercentOfTotal':  8.0, 'changeInRank':  0, 'changeInPercentOfTotal':  0.0},
             ]
  dl = tcbst.DictList(iterable)
  result =  dl.find('s1')
  assert result == (1, 9.0), "expected (1, 9.0), but got %s" % str(result)
  result =  dl.find('s2')
  assert result == (0, 10.0), "expected (0, 10.0), but got %s" % str(result)
  result =  dl.find('s3')
  assert result == (2, 8.0), "expected (2, 8.0), but got %s" % str(result)
  try:
    result =  dl.find('s3')
  except KeyError:
    pass
  except Exception, x:
    assert False, "expected KeyError on key not found, but got %s" % str(x)
  for i, (x, y) in enumerate(zip (iter(iterable), iter(dl))):
    assert x == y, "when iterating at index %d, expected %s, but got %s" % (i, x, y)
