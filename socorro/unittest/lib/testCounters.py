import socorro.lib.counters as counters
import socorro.unittest.testlib.expectations as exp
import socorro.lib.util as sutil

import time

def testCounterOverTime1():
    c = counters.CounterOverTime(5)
    assert c.historyLengthInMinutes == 5
    assert c.currentMinute == 0
    assert c.currentCounter == 0
    assert c.timeFunction == time.time

def testCounterOverTime2():
    c = counters.CounterOverTime(5)
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
    c = counters.CounterOverTime(5, timeFunction=dummyTimeFunction)
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
    p = counters.CounterPool(config)
    timeFunctions = [exp.DummyObjectWithExpectations() for x in range(6)]
    for t in timeFunctions:
        for x in range(10):
            for y in range(5):
                t.expect('__call__', (), {}, (x + 1) * 60)
    for t in timeFunctions:
        for x in range(3):
            t.expect('__call__', (), {}, 660) #account for reads in meanAndStandardDeviation
    clist = [counters.CounterOverTime(5, timeFunction=t) for t in timeFunctions]
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
    p = counters.CounterPool(config)
    timeFunctions = [exp.DummyObjectWithExpectations() for x in range(6)]
    for t in timeFunctions[:-1]:
        for x in range(10):
            for y in range(5):
                t.expect('__call__', (), {}, (x + 1) * 60)
    for t in timeFunctions:
        for x in range(4):
            t.expect('__call__', (), {}, 660) #account for reads in meanAndStandardDeviation
    clist = [counters.CounterOverTime(5, timeFunction=t) for t in timeFunctions]
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
