# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import urllib2 as u2
import logging
logger = logging.getLogger("webapi")

import socorro.lib.util as util
import socorro.webapi.webapiService as webapi
import socorro.lib.datetimeutil as dtutil

from socorro.external.postgresql.tcbs import which_tcbs
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
                                           dtutil.string_to_datetime,
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
      table_type = which_tcbs(self.connection.cursor(), {},
                              parameters['product'], parameters['version'])
      impl = {
        "old": classic.SignatureHistoryClassic(self.configContext),
        "new": modern.SignatureHistoryModern(self.configContext),
      }
      return impl[table_type].signatureHistory(parameters, self.connection)
    finally:
      self.connection.close()
