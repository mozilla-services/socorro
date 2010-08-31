import datetime as dt
import web
import urllib
import urllib2
import functools
import json

import socorro.webapi.webapiService as webapi
import socorro.lib.datetimeutil as dtutil

web.webapi.internalerror = web.debugerror

#===============================================================================
class UnknownProcessorException(Exception):
  pass

#===============================================================================
class RegistrarBaseService(webapi.JsonServiceBase):
  #-----------------------------------------------------------------------------
  def __init__(self, context, aRegistrar):
    super(RegistrarBaseService, self).__init__(context)
    self.registrar = aRegistrar

#===============================================================================
class RegistrationService(RegistrarBaseService):
  #-----------------------------------------------------------------------------
  def __init__(self, context, aRegistrar):
    super(RegistrationService, self).__init__(context, aRegistrar)
  #-----------------------------------------------------------------------------
  uri = '/201006/register/processor'
  #-----------------------------------------------------------------------------
  def POST(self):
    data = web.input()
    processorName = data['name']
    processorStatus = data['status']
    self.context.logger.debug('RegistrationService request for %s',
                              processorName)
    self.registrar.register(processorName, processorStatus)

#===============================================================================
class DeregistrationService(RegistrarBaseService):
  #-----------------------------------------------------------------------------
  def __init__(self, context, aRegistrar):
    super(DeregistrationService, self).__init__(context, aRegistrar)
  #-----------------------------------------------------------------------------
  uri = '/201006/deregister/processor'
  #-----------------------------------------------------------------------------
  def POST(self):
    data = web.input()
    processorName = data['name']
    self.context.logger.debug('DeregistrationService request for %s',
                              processorName)
    self.registrar.deregister(processorName)

#===============================================================================
class ListService(RegistrarBaseService):
  #-----------------------------------------------------------------------------
  def __init__(self, context, aRegistrar):
    super(ListService, self).__init__(context, aRegistrar)
  #-----------------------------------------------------------------------------
  uri = '/201006/processors'
  #-----------------------------------------------------------------------------
  def get(self, *args):
    return self.registrar.processors.keys()

#===============================================================================
class TardyService(RegistrarBaseService):
  #-----------------------------------------------------------------------------
  def __init__(self, context, aRegistrar):
    super(TardyService, self).__init__(context, aRegistrar)
  #-----------------------------------------------------------------------------
  uri = '/201006/tardy'
  #-----------------------------------------------------------------------------
  def get(self, *args):
    return [x for x in self.registrar.tardyIter()]

#===============================================================================
class ProblemService(RegistrarBaseService):
  #-----------------------------------------------------------------------------
  def __init__(self, context, aRegistrar):
    super(ProblemService, self).__init__(context, aRegistrar)
  #-----------------------------------------------------------------------------
  uri = '/201006/problem'
  #-----------------------------------------------------------------------------
  def get(self, *args):
    return [x for x in self.registrar.problemIter()]

#===============================================================================
class GetProcessorService(RegistrarBaseService):
  #-----------------------------------------------------------------------------
  def __init__(self, context, aRegistrar):
    super(GetProcessorService, self).__init__(context, aRegistrar)
  #-----------------------------------------------------------------------------
  uri = '/201006/processor/status/(.*)'
  #-----------------------------------------------------------------------------
  def get(self, *args):
    processorName = args[0]
    timestamp, status = self.registrar.getProcessorTuple(processorName)
    return ["%4d-%02d-%02d %02d:%02d:%02d.%d" % (timestamp.year,
                                                 timestamp.month,
                                                 timestamp.day,
                                                 timestamp.hour,
                                                 timestamp.minute,
                                                 timestamp.second,
                                                 timestamp.microsecond),
            status,
           ]

#===============================================================================
class ProcessorForwardingService(RegistrarBaseService):
  """This class is a web service class that implements forwarding a uri to
  a known processor.
  """
  #-----------------------------------------------------------------------------
  def __init__(self, context, aRegistrar):
    super(ProcessorForwardingService, self).__init__(context, aRegistrar)
  #-----------------------------------------------------------------------------
  uri = '/201006/processor/(.*?)/(.*)'
  #uriArgNames = ['processorName', 'uri']
  #uriArgTypes = [str, str]
  #uriDoc = __doc__
  #-----------------------------------------------------------------------------
  def get(self, *args):
    try:
      f = urllib2.urlopen('http://%s/%s' % args)
    except urllib2.HTTPError, x:
      if x.code == 404:
        raise web.notfound()
      raise
    try:
      return json.loads('\n'.join(f.readlines()))
    finally:
      f.close()
  #-----------------------------------------------------------------------------
  def POST(self, *args):
    data = web.input()
    params = urllib.urlencode(data)
    try:
      f = urllib2.urlopen('http://%s/%s' % args, params)
      f.close()
    except urllib2.HTTPError, x:
      if x.code == 404:
        raise web.notfound()
      raise

#===============================================================================
class ProcessorStatsService(RegistrarBaseService):
  """This class is a web service class that implements forwarding a uri to
  a known processor.
  """
  #-----------------------------------------------------------------------------
  def __init__(self, context, aRegistrar):
    super(ProcessorStatsService, self).__init__(context, aRegistrar)
  #-----------------------------------------------------------------------------
  uri = '/201008/stats/(.*)'
  #uriArgNames = ['statName']
  #uriArgTypes = [str]
  #uriDoc = 'the name of the statistic to aggregate from the processors'
  knownProcessorStats = { 'processed': 'singleValueForSummation',
                          'missing': 'singleValueForSummation',
                          'failures': 'singleValueForSummation',
                          'breakpadErrors': 'singleValueForSummation',
                          'processTime': 'processTimeAverage',
                          'totalTimeForProcessing': 'totalProcessTimeAverage',
                          'mostRecent': 'singleValueForMax',
                          'all': 'all',
                        }
  #-----------------------------------------------------------------------------
  def statsFromProcessors(self, statName):
    listOfStats = []
    for aProcessor in self.registrar.processors.keys():
      f = urllib2.urlopen('http://%s/201007/stats/%s' % (aProcessor, statName))
      linesFromProcessor = f.readlines()
      listOfStats.append(json.loads(linesFromProcessor[0]))
    return listOfStats
  #-----------------------------------------------------------------------------
  def singleValueForSummation (self, statName):
    listOfStats = self.statsFromProcessors(statName)
    try:
      return sum(x for x in listOfStats if x is not None)
    except ValueError:
      return 0
  #-----------------------------------------------------------------------------
  def singleValueForMax (self, statName):
    listOfStats = self.statsFromProcessors(statName)
    try:
      return max(x for x in listOfStats if x is not None)
    except ValueError:
      return 0
  #---------------------------------------------------------------------------
  @staticmethod
  def addTuples(x, y):
      return tuple(i + j for i, j in zip(x, y))
  #-----------------------------------------------------------------------------
  def processTimeAverage(self, statName):
    listOfStats = []
    for aProcessor in self.registrar.processors.keys():
      f = urllib2.urlopen('http://%s/201008/process/time/accumulation' %
                              (aProcessor,))
      count, timeDeltaAsString = json.loads(f.readline())
      newTuple = (count, dtutil.stringToTimeDelta(timeDeltaAsString))
      listOfStats.append(newTuple)
    count, durationSum = functools.reduce(lambda x,y: self.addTuples(x, y),
                                          listOfStats,
                                          (0, dt.timedelta(0)))
    try:
      return durationSum / count
    except ZeroDivisionError:
      return 0.0
  #-----------------------------------------------------------------------------
  def totalProcessTimeAverage(self, statName):
    listOfStats = []
    for aProcessor in self.registrar.processors.keys():
      f = urllib2.urlopen('http://%s/201008/total/process/time' %
                              (aProcessor,))
      count, timeDeltaAsString = json.loads(f.readline())
      newTuple = (count, dtutil.stringToTimeDelta(timeDeltaAsString))
      listOfStats.append(newTuple)
    count, durationSum = functools.reduce(lambda x,y: self.addTuples(x, y),
                                          listOfStats,
                                          (0, dt.timedelta(0)))
    try:
      return durationSum / count
    except ZeroDivisionError:
      return 0.0
  #-----------------------------------------------------------------------------
  def fetchStat(self, statName):
    dispatchedFunction = \
        self.__getattribute__( \
             ProcessorStatsService.knownProcessorStats[statName])
    return dispatchedFunction(statName)
  #-----------------------------------------------------------------------------
  def get(self, *args):
    statName = args[0]
    if statName not in ProcessorStatsService.knownProcessorStats.keys():
      raise web.notfound()
    if statName != 'all':
      result = self.fetchStat(statName)
      self.registrar.logger.debug('stat result: %s', str(result))
      return webapi.sanitizeForJson(result)
    else:
      result = {}
      for aStatName in ProcessorStatsService.knownProcessorStats.keys():
        if aStatName != 'all':
          result[aStatName] = self.fetchStat(aStatName)
      return webapi.sanitizeForJson(result)

#===============================================================================
class RegistrarServicesQuery(RegistrarBaseService):
  #-----------------------------------------------------------------------------
  def __init__(self, context, aRegistrar):
    super(RegistrarServicesQuery, self).__init__(context, aRegistrar)
  #-----------------------------------------------------------------------------
  uri = '/services'
  #-----------------------------------------------------------------------------
  def get(self, *args):
    return dict(((x.__name__, x.uri) for x in self.registrar.services))

#===============================================================================
class Registrar(object):
  #-----------------------------------------------------------------------------
  def __init__(self, config):
    super(Registrar, self).__init__()
    self.config = config
    self.logger = config.logger
    self.checkinDeadline = config.processorCheckInFrequency + \
                           config.checkInFrequencyForgiveness
    self.processors = {}

  #-----------------------------------------------------------------------------
  def register(self, processorName, processorStatus):
    self.processors[processorName] = (dt.datetime.now(), processorStatus)
    if processorStatus != 'ok':
      self.logger.warning('processor %s registers with a status of: %s',
                          processorName,
                          processorStatus)

  #-----------------------------------------------------------------------------
  def deregister(self, processorName):
    try:
      del self.processors[processorName]
    except KeyError:
      raise UnknownProcessorException('%s was not registered' % processorName)

  #-----------------------------------------------------------------------------
  def tardyIter(self):
    for processorName, registrationTuple in self.processors.iteritems():
      timestamp, status = registrationTuple
      if dt.datetime.now() - timestamp > self.checkinDeadline:
        yield processorName

  #-----------------------------------------------------------------------------
  def problemIter(self):
    for processorName, registrationTuple in self.processors.iteritems():
      timestamp, status  = registrationTuple
      if status != 'ok':
        yield processorName

  #-----------------------------------------------------------------------------
  def getProcessorTuple(self, processorName):
    try:
      return self.processors[processorName]
    except KeyError:
      raise UnknownProcessorException('%s was not registered' % processorName)

