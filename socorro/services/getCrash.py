# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
logger = logging.getLogger("webapi")

import socorro.lib.util as util
import socorro.webapi.webapiService as webapi
import web
import json

from socorro.external.postgresql.priorityjobs import Priorityjobs

datatype_options = ('meta', 'raw_crash', 'processed')
crashStorageFunctions = ('fetchMeta', 'fetchRaw', 'fetchProcessed')
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
  uri = '/crash/(.*)/by/uuid/(.*)'
  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    convertedArgs = webapi.typeConversion([dataTypeOptions,str], args)
    parameters = util.DotDict(zip(['datatype','uuid'], convertedArgs))
    logger.debug("GetCrash get %s", parameters)
    self.crashStorage = self.crashStoragePool.crashStorage()
    function_name = datatype_function_associations[parameters.datatype]
    function = self.__getattribute__(function_name)
    return function(parameters.uuid)

  def fetchProcessed(self, uuid):
    # FIXME hackerschool hack
    crashdir = '/home/rhelmer/dev/socorro/'
    crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'
    with open('%s/%s.jsonz' % (crashdir, crash_id)) as f:
        return json.loads(f.read())

    try:
        return self.crashStorage.get_processed(uuid)
    except Exception:
        try:
            raw = self.fetchRaw(uuid)
            j = Priorityjobs(config=self.context)
            j.create(uuid=uuid)
        except Exception:
            raise web.webapi.NotFound()
        raise webapi.Timeout()

  def fetchMeta(self, uuid):
    # FIXME hackerschool hack
    crashdir = '/home/rhelmer/dev/socorro/'
    crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'
    with open('%s/%s.json' % (crashdir, crash_id)) as f:
        return json.loads(f.read())

    return self.crashStorage.get_meta(uuid)

  def fetchRaw(self, uuid):
    return (self.crashStorage.get_raw_dump(uuid), "application/octet-stream")
