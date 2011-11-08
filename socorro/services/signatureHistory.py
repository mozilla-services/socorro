import datetime as dt
import urllib2 as u2
import logging
logger = logging.getLogger("webapi")

import socorro.lib.util as util
import socorro.webapi.webapiService as webapi
import socorro.database.database as db
import socorro.lib.datetimeutil as dtutil

from socorro.services.topCrashBySignatureTrends import whichTCBS
import socorro.services.sighistory.classic as classic
import socorro.services.sighistory.modern as modern

class SignatureHistory(webapi.JsonServiceBase):

  def __init__(self, configContext):
    super(SignatureHistory, self).__init__(configContext)
    self.configContext = configContext
    logger.debug('SignatureHistory __init__')

  uri = ('/topcrash/sig/trend/history/p/(.*)/v/(.*)/sig/(.*)/end/(.*)/'
         'duration/(.*)/steps/(.*)')

  def get(self, *args):
    convertedArgs = webapi.typeConversion([str, str, u2.unquote,
                                           dtutil.datetimeFromISOdateString,
                                           dtutil.strHoursToTimeDelta, int],
                                          args)
    parameters = util.DotDict(zip(['product', 'version', 'signature',
                                   'endDate', 'duration', 'steps'],
                                 convertedArgs))
    parameters['productVersionCache'] = self.context['productVersionCache']
    logger.debug("SignatureHistory get %s", parameters)
    self.connection = self.database.connection()
    #logger.debug('connection: %s', self.connection)
    try:
      table_type = whichTCBS(self.connection.cursor(), {},
                             parameters['product'], parameters['version'])
      impl = {
        "old": classic.SignatureHistoryClassic(self.configContext),
        "new": modern.SignatureHistoryModern(self.configContext),
      }
      return impl[table_type].signatureHistory(parameters, self.connection)
    finally:
      self.connection.close()
