import socorro.lib.stats as stats
import socorro.unittest.testlib.expectations as exp
import socorro.lib.util as sutil

import time
import datetime as dt

def testCounterOverTime1():
    c = stats.CounterOverTime(5)
    assert c.historyLengthInMinutes == 5
    assert c.currentMinute == 0
    assert c.currentCounter == 0
    assert c.timeFunction == time.time

def testCounterOverTime2():
    c = stats.CounterOverTime(5)
    c.increment()
    assert c.currentMinute != 0
    assert c.currentCounter == 1
    assert c.history[0] == (0,0)

def testCounterOverTime3():
    dummyTimeFunction = exp.DummyObjectWithExpectations()
    # set function to return 1..6 each 5 times
    for x in range(10):
        for y in range(5):
            dummyTimeFunction.expect('__call__', (), {}, (x + 1) * 60)
    c = stats.CounterOverTime(5, timeFunction=dummyTimeFunction)
    for y in range(10):
        for x in range(4):
            c.increment()
            #print c.currentMinute, y + 1
            assert c.currentMinute == y + 1
            assert c.currentCounter == x + 1
        assert c.currentCounter == 4
        assert c.currentMinute == y + 1
        r = c.read()
        #print r
        assert r == 4 * min(y, 5)

def testCounterPool1():
    """Test a pool of 6 counters all in perfect lock step"""
    config = sutil.DotDict({'logger':sutil.SilentFakeLogger()})
    p = stats.CounterPool(config)
    timeFunctions = [exp.DummyObjectWithExpectations() for x in range(6)]
    for t in timeFunctions:
        for x in range(10):
            for y in range(5):
                t.expect('__call__', (), {}, (x + 1) * 60)
    for t in timeFunctions:
        for x in range(3):
            t.expect('__call__', (), {}, 660) #account for reads in meanAndStandardDeviation
    clist = [stats.CounterOverTime(5, timeFunction=t) for t in timeFunctions]
    for k,c in zip('abcdef', clist):
        p[k] = c
    for x in range(50):
        for c in clist:
            c.increment()
    for c in clist:
        r = c.read()
        assert r == 25
    r = p.meanAndStandardDeviation()
    print r
    assert  r == (25.0, 0.0)

def testCounterPool2():
    """Test a pool of 6 counters 5 in lock step and 1 doing nothing"""
    config = sutil.DotDict({'logger':sutil.SilentFakeLogger()})
    p = stats.CounterPool(config)
    timeFunctions = [exp.DummyObjectWithExpectations() for x in range(6)]
    for t in timeFunctions[:-1]:
        for x in range(10):
            for y in range(5):
                t.expect('__call__', (), {}, (x + 1) * 60)
    for t in timeFunctions:
        for x in range(4):
            t.expect('__call__', (), {}, 660) #account for reads in meanAndStandardDeviation
    clist = [stats.CounterOverTime(5, timeFunction=t) for t in timeFunctions]
    for k,c in zip('abcdef', clist):
        p[k] = c
    for x in range(50):
        for c in clist[:-1]:
            c.increment()
    for c in clist[:-1]:
        r = c.read()
        assert r == 25
    assert clist[-1].read() == 0
    r = p.underPerforming()
    print r
    assert r == ['f']

def testDurationAccumulatorOverTime1():
    c = stats.DurationAccumulatorOverTime(5)
    assert c.historyLengthInMinutes == 5
    assert c.currentMinute == 0
    assert c.currentCounter == 0
    assert c.timeFunction == time.time
    assert c.timeDeltaAccumulator == dt.timedelta(0)
    assert c.started == dt.timedelta(0)

def testDurationAccumulatorOverTime2():
    c = stats.DurationAccumulatorOverTime(5)
    c.start()
    assert c.started != dt.timedelta(0)
    time.sleep(1.0)
    c.end()
    assert c.currentCounter == 1
    assert c.timeDeltaAccumulator != dt.timedelta(0)
    assert c.history[0] == (0,0,dt.timedelta(0))

#def testDurationAccumulatorOverTime3():
    #dummyTimeFunction = exp.DummyObjectWithExpectations()
    ## set function to return 1..6 each 5 times
    #for x in range(10):
        #for y in range(5):
            #dummyTimeFunction.expect('__call__', (), {}, (x + 1) * 60)
    #c = stats.DurationAccumulatorOverTime(5, timeFunction=dummyTimeFunction)
    #for y in range(10):
        #for x in range(4):
            #c.increment()
            ##print c.currentMinute, y + 1
            #assert c.currentMinute == y + 1
            #assert c.currentCounter == x + 1
        #assert c.currentCounter == 4
        #assert c.currentMinute == y + 1
        #r = c.read()
        ##print r
        #assert r == 4 * min(y, 5)

def testMostRecent():
    r = stats.MostRecent()
    assert r.read() is None
    now = dt.datetime.now()
    r.put(now)
    assert now == r.read()
    next = dt.datetime.now()
    r.put(next)
    assert next == r.read()

import random
def testMostRecentPool():
    config = sutil.DotDict({'logger':sutil.SilentFakeLogger()})
    rp = stats.MostRecentPool(config)
    listOfStats = [rp.getStat(x) for x in 'abcdef']
    for x in listOfStats:
        assert type(x) == stats.MostRecent, 'expected %s but got %s' % \
                                            (stats.MostRecent,
                                             type(x))
    values = range(len(listOfStats))
    random.shuffle(values)
    for stat, i in zip(listOfStats, values):
        stat.put(i)
    assert rp.read() == len(listOfStats) - 1

