import datetime as dt
import urllib as url
import urllib2 as url2
import web.webapi
import json
import cStringIO
import gzip
import logging
logger = logging.getLogger("webapi")

import socorro.lib.util as util
import socorro.webapi.webapiService as webapi
import socorro.database.database as db
import socorro.lib.datetimeutil as dtutil
import socorro.storage.crashstorage as cs
import socorro.lib.ooid as sooid

datatype_options = ('meta', 'raw_crash', 'processed', 'jsonz', 'compressed_processed')
crashStorageFunctions = ('get_meta', 'get_raw_dump', 'get_processed', 'get_processed_compressed', 'get_processed_compressed')
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
    if not sooid.isValid(ooid):
      raise web.webapi.BadRequest()
    try:
      return crashStorage.get_meta(ooid)
    except cs.OoidNotFoundException:
      raise web.webapi.NotFound(message="ooid '%s' is not in the system" % ooid)
  #-----------------------------------------------------------------------------------------------------------------
  def get_raw_dump(self, ooid, crashStorage):
    if not sooid.isValid(ooid):
      raise web.webapi.BadRequest()
    try:
      return (crashStorage.get_raw_dump(ooid), "application/octet-stream")
    except cs.OoidNotFoundException:
      raise web.webapi.NotFound(message="ooid '%s' is not in the system" % ooid)
  #-----------------------------------------------------------------------------------------------------------------
  def get_processed(self, ooid, crashStorage):
    if not sooid.isValid(ooid):
      raise web.webapi.BadRequest()
    try:
      return crashStorage.get_processed(ooid)
    except cs.OoidNotFoundException:
      try:
        crashStorage.get_meta(ooid)
      except cs.OoidNotFoundException:
        raise web.webapi.NotFound(message="ooid '%s' is not in the system" % ooid)
      data = {'ooid': ooid}
      params = url.urlencode(data)
      try:
        f = url2.urlopen(self.context.prioritySubmissionUrl, params)
        f.close()
      except url2.HTTPError:
        # TODO: replace with something more appropriate?
        raise
      logger.debug('about to raise Accepted')
      raise web.webapi.Accepted()
  #-----------------------------------------------------------------------------------------------------------------
  def get_processed_compressed(self, ooid, crashStorage):
    processed = self.get_processed(ooid, crashStorage)
    json_processed = json.dumps(processed)
    buffer = cStringIO.StringIO()
    f = gzip.GzipFile(mode='w', fileobj=buffer)
    f.write(json_processed)
    f.close()
    jsonz = buffer.getvalue()
    buffer.close()
    return (jsonz, "application/octet-stream")

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