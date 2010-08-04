import datetime as dt
import web
import urllib
import urllib2
import json

import socorro.webapi.webapiService as webapi

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

