import collections
import functools
import math
import threading
import time

from socorro.lib.datetimeutil import utc_now

class UndefinedCounterActionException(Exception):
    pass

#===============================================================================
class Statistic(object):
    #---------------------------------------------------------------------------
    def __init__(self):
        pass
    #---------------------------------------------------------------------------
    def read(self):
        return None
    #---------------------------------------------------------------------------
    def __repr__(self):
        return str(self.__dict__)

#===============================================================================
class StatsPool(dict):
    #---------------------------------------------------------------------------
    def __init__(self,
                 config,
                 statsClass=Statistic,
                 statsInitArgs=(),
                 statsInitKwargs={}):
        self.statsClass = statsClass
        self.statsInitArgs = statsInitArgs
        self.statsInitKwargs = statsInitKwargs
        self.logger = config.logger
        self.logger.debug("creating %s", self.__class__.__name__)
    #---------------------------------------------------------------------------
    def cleanup (self):
        for name, stat in self.iteritems():
            try:
                stat.close()
                self.logger.debug("counter %s closed", name)
            except:
                sutil.reportExceptionAndContinue(self.logger)
    #---------------------------------------------------------------------------
    def getStat(self, name=None):
        if name is None:
            name = threading.currentThread().getName()
        if name not in self:
            self.logger.debug("creating %s for %s",
                              self.statsClass.__name__,
                              name)
            self[name] = c = self.statsClass(*self.statsInitArgs,
                                               **self.statsInitKwargs)
            return c
        return self[name]
    #---------------------------------------------------------------------------
    def read(self):
        return None


#===============================================================================
class CounterOverTime(Statistic):
    #---------------------------------------------------------------------------
    def __init__(self, historyLengthInMinutes, timeFunction=time.time):
        super(CounterOverTime, self).__init__()
        self.historyLengthInMinutes = historyLengthInMinutes
        self.history = collections.deque(maxlen=historyLengthInMinutes)
        self.currentMinute = 0
        self.currentCounter = 0
        self.timeFunction = timeFunction
    #---------------------------------------------------------------------------
    def nowMinute(self):
        return int(self.timeFunction()) / 60
    #---------------------------------------------------------------------------
    def pushOldCounter(self, minute):
        self.history.append((self.currentMinute, self.currentCounter))
        self.currentMinute = minute
        self.currentCounter = 0
    #---------------------------------------------------------------------------
    def increment(self,now=None):
        if now is None:
            now = self.nowMinute()
        if self.currentMinute != now:
            self.pushOldCounter(now)
        self.currentCounter += 1
    #---------------------------------------------------------------------------
    def read(self, now=None):
        if now is None:
            now = self.nowMinute()
        if self.currentMinute != now:
            self.pushOldCounter(now)
        sum = 0
        for minute, count in self.history:
            if minute >= now - self.historyLengthInMinutes:
                sum += count
        return sum

#===============================================================================
class CounterPool(StatsPool):
    #---------------------------------------------------------------------------
    def __init__(self,
                 config,
                 statsClass=CounterOverTime,
                 statsInitArgs=(5,),
                 statsInitKwargs={}):
        super(CounterPool, self).__init__(config,
                                          statsClass,
                                          statsInitArgs,
                                          statsInitKwargs)
    #---------------------------------------------------------------------------
    def numberOfMinutes (self):
        return len(self.values()[0].history)
    #---------------------------------------------------------------------------
    def read (self):
        return functools.reduce(lambda x, y: x+y.read(), self.values(), 0)
    #---------------------------------------------------------------------------
    def average (self):
        #sum = functools.reduce(lambda x, y: x+y.read(), self.values(), 0)
        sum = self.read()
        try:
            return float(sum) / len(self)
        except ZeroDivisionError:
            return 0.0
    #---------------------------------------------------------------------------
    def meanAndStandardDeviation (self):
        mean = self.average()
        sum_squares = functools.reduce(lambda x, y: x + (y.read() - mean)**2,
                                       self.values(),
                                       0)
        try:
            standard_deviation = math.sqrt(sum_squares / len(self))
            return (mean, standard_deviation)
        except ZeroDivisionError:
            return (0.0, 0.0)
    #---------------------------------------------------------------------------
    def underPerforming (self):
        mean, stddev = self.meanAndStandardDeviation()
        threshold = mean - stddev
        return [x for x,y in self.iteritems() if y.read() < threshold]


import datetime as dt
#===============================================================================
class DurationAccumulatorOverTime(CounterOverTime):
    #---------------------------------------------------------------------------
    def __init__(self,
                 historyLengthInMinutes,
                 timeFunction=time.time,
                 datetimeNowFunction=utc_now):
        super(DurationAccumulatorOverTime,
              self).__init__(historyLengthInMinutes,
                             timeFunction)
        self.timeDeltaAccumulator = dt.timedelta(0)
        self.started = None
        self.datetimeNowFunction = datetimeNowFunction
    #---------------------------------------------------------------------------
    def pushOldCounter(self, minute):
        self.history.append((self.currentMinute,
                             self.currentCounter,
                             self.timeDeltaAccumulator))
        self.currentMinute = minute
        self.timeDeltaAccumulator = dt.timedelta(0)
        self.currentCounter = 0
    #---------------------------------------------------------------------------
    def start(self, starttime=None):
        if starttime:
            self.started = starttime
        else:
            self.started = self.datetimeNowFunction()
    #---------------------------------------------------------------------------
    def end(self, endtime=None, now=None):
        if not endtime:
            endtime = self.datetimeNowFunction()
        try:
            duration = endtime - self.started
            if now is None:
                now = self.nowMinute()
            if self.currentMinute != now:
                self.pushOldCounter(now)
            self.timeDeltaAccumulator += duration
            self.currentCounter += 1
            self.started = None
        except TypeError:
            pass
    #---------------------------------------------------------------------------
    def increment(self,now=None):
        raise UndefinedCounterActionException()
    #---------------------------------------------------------------------------
    def read(self, now=None):
        if now is None:
            now = self.nowMinute()
        if self.currentMinute != now:
            self.pushOldCounter(now)
        sum = 0
        duration_sum = dt.timedelta(0)
        for minute, count, durations in self.history:
            if minute >= now - self.historyLengthInMinutes:
                sum += count
                duration_sum += durations
        return (sum, duration_sum)
    #---------------------------------------------------------------------------
    def average(self):
        sum, duration_sum = self.read()
        try:
            return duration_sum / float(sum)
        except ZeroDivisionError:
            return 0.0

#===============================================================================
class DurationAccumulatorPool(CounterPool):
    #---------------------------------------------------------------------------
    def __init__(self,
                 config,
                 statsClass=DurationAccumulatorOverTime,
                 statsInitArgs=(5,),
                 statsInitKwargs={}):
        super(DurationAccumulatorPool, self).__init__(config,
                                                      statsClass,
                                                      statsInitArgs,
                                                      statsInitKwargs)
    #---------------------------------------------------------------------------
    @staticmethod
    def addTuples(x, y):
        return tuple(i + j for i, j in zip(x, y))
    #---------------------------------------------------------------------------
    def sumDurations (self):
        return functools.reduce(lambda x,y: self.addTuples(x, y.read()),
                                self.values(),
                                (0, dt.timedelta(0)))
    #---------------------------------------------------------------------------
    def read (self):
        sum, duration_sum = self.sumDurations()
        try:
            return duration_sum / sum
        except ZeroDivisionError:
            return 0.0
    #---------------------------------------------------------------------------
    def meanAndStandardDeviation (self):
        raise UndefinedCounterActionException()
    #---------------------------------------------------------------------------
    def underPerforming (self):
        raise UndefinedCounterActionException()

#===============================================================================
class MostRecent(Statistic):
    #---------------------------------------------------------------------------
    def __init__(self):
        super(MostRecent, self).__init__()
        self.mostRecentThing = None
    #---------------------------------------------------------------------------
    def put(self, thing):
        self.mostRecentThing = thing
    #---------------------------------------------------------------------------
    def read(self):
        return self.mostRecentThing

#===============================================================================
class MostRecentPool(StatsPool):
    #---------------------------------------------------------------------------
    def __init__(self,
                 config,
                 statsClass=MostRecent,
                 statsInitArgs=(),
                 statsInitKwargs={}):
        super(MostRecentPool, self).__init__(config,
                                             statsClass,
                                             statsInitArgs,
                                             statsInitKwargs)
    #---------------------------------------------------------------------------
    def read(self):
        try:
            return max(x.read() for x in self.values())
        except ValueError:
            return None
