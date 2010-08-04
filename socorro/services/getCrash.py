import datetime as dt
import urllib as url
import urllib2 as url2
import logging
logger = logging.getLogger("webapi")

import socorro.lib.util as util
import socorro.webapi.webapiService as webapi
import socorro.database.database as db
import socorro.lib.datetimeutil as dtutil
import socorro.storage.crashstorage as cs

datatype_options = ('meta', 'raw_crash', 'processed')
crashStorageFunctions = ('get_meta', 'get_raw_dump', 'get_processed')
datatype_function_associations = dict(zip(datatype_options, crashStorageFunctions))

class NotADataTypeOption(Exception):
  def __init__(self, reason):
    #super(NotADataTypeOption, self).__init__("%s must be one of %s" % (reason, ','.join(datatype_options))
    Exception.__init__("%s must be one of %s" % (reason, ','.join(datatype_options)))

def dataTypeOptions(x):
  if x in datatype_options:
    return x
  raise NotADataTypeOption(x)

#=================================================================================================================
class GetCrash(webapi.JsonServiceBase):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, configContext):
    super(GetCrash, self).__init__(configContext)
    logger.debug('GetCrash __init__')
  #-----------------------------------------------------------------------------------------------------------------
  uri = '/201008/crash/(.*)/by/ooid/(.*)'
  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    convertedArgs = webapi.typeConversion([dataTypeOptions,str], args)
    parameters = util.DotDict(zip(['datatype','ooid'], convertedArgs))
    logger.debug("GetCrash get %s", parameters)
    crashStorage = self.context.crashStoragePool.crashStorage()
    function_name = datatype_function_associations[parameters.datatype]
    function = self.__getattribute__(function_name)
    return function(parameters.ooid, crashStorage)
  #-----------------------------------------------------------------------------------------------------------------
  def get_meta(self, ooid, crashStorage):
    return crashStorage.get_meta(ooid)
  #-----------------------------------------------------------------------------------------------------------------
  def get_raw_dump(self, ooid, crashStorage):
    return (crashStorage.get_raw_dump(ooid), "application/octet-stream")
  #-----------------------------------------------------------------------------------------------------------------
  def get_processed(self, ooid, crashStorage):
    try:
      return crashStorage.get_processed(ooid)
    except cs.OoidNotFoundException:
      data = {'ooid': ooid}
      params = url.urlencode(data)
      try:
        f = url2.urlopen(self.context.prioritySubmissionUrl, params)
        f.close()
      except urllib2.HTTPError:
        # TODO: replace with something more appropriate?
        raise
      return 'no'

#=================================================================================================================
class GetCrash201005(webapi.JsonServiceBase):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, configContext):
    super(GetCrash201005, self).__init__(configContext)
    logger.debug('GetCrash __init__')
  #-----------------------------------------------------------------------------------------------------------------
  uri = '/201005/crash/(.*)/by/uuid/(.*)'
  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    convertedArgs = webapi.typeConversion([dataTypeOptions,str], args)
    parameters = util.DotDict(zip(['datatype','uuid'], convertedArgs))
    logger.debug("GetCrash get %s", parameters)
    crashStorage = self.context.crashStoragePool.crashStorage()
    function_name = datatype_function_associations[parameters.datatype]
    function = crashStorage.__getattribute__(function_name)
    if function_name == 'get_raw_dump':
      return(function(parameters.uuid), "application/octet-stream")
    return function(parameters.uuid)