import collections
import functools
import math
import threading
import time

#===============================================================================
class Counter(object):
    #---------------------------------------------------------------------------
    def __init__(self):
        pass
    #---------------------------------------------------------------------------
    def increment(self):
        pass
    #---------------------------------------------------------------------------
    def read(self):
        pass
    #---------------------------------------------------------------------------
    def close(self):
        pass

#===============================================================================
class CounterOverTime(Counter):
    #---------------------------------------------------------------------------
    def __init__(self, historyLengthInMinutes, timeFunction=time.time):
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
        #print now
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
class CounterPool(dict):
    #---------------------------------------------------------------------------
    def __init__(self,
                 config,
                 counterClass=CounterOverTime,
                 counterInitArgs=(5,),
                 counterInitKwargs={}):
        super(CounterPool, self).__init__()
        self.counterClass = counterClass
        self.counterInitArgs = counterInitArgs
        self.counterInitKwargs = counterInitKwargs
        self.logger = config.logger
        self.logger.debug("creating CounterPool")

    #---------------------------------------------------------------------------
    def counter(self, name=None):
        if name is None:
            name = threading.currentThread().getName()
        if name not in self:
            self.logger.debug("creating %s for %s",
                              self.counterClass.__name__,
                              name)
            self[name] = c = self.counterClass(*self.counterInitArgs,
                                               **self.counterInitKwargs)
            return c
        return self[name]

    #---------------------------------------------------------------------------
    def cleanup (self):
        for name, counter in self.iteritems():
            try:
                crashStore.close()
                self.logger.debug("counter %s closed", name)
            except:
                sutil.reportExceptionAndContinue(self.logger)

    #---------------------------------------------------------------------------
    def read (self):
        return functools.reduce(lambda x, y: x+y.read(), self.values(), 0)

    #---------------------------------------------------------------------------
    def average (self):
        sum = functools.reduce(lambda x, y: x+y.read(), self.values(), 0)
        return float(sum) / len(self)

    #---------------------------------------------------------------------------
    def meanAndStandardDeviation (self):
        mean = self.average()
        sum_squares = functools.reduce(lambda x, y: x + (y.read() - mean)**2,
                                       self.values(),
                                       0)
        standard_deviation = math.sqrt(sum_squares / len(self))
        return (mean, standard_deviation)

    #---------------------------------------------------------------------------
    def underPerforming (self):
        mean, stddev = self.meanAndStandardDeviation()
        threshold = mean - stddev
        return [x for x,y in self.iteritems() if y.read() < threshold]