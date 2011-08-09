import datetime as dt
import urllib2 as u2
import logging
logger = logging.getLogger("webapi")

import socorro.lib.util as util
import socorro.webapi.webapiService as webapi
import socorro.database.database as db
import socorro.lib.datetimeutil as dtutil

class SignatureHistoryModern(webapi.JsonServiceBase):

  def __init__(self, configContext):
    super(SignatureHistoryModern, self).__init__(configContext)
    logger.debug('SignatureHistoryModern __init__')

  uri = ('/200911/topcrash/sig/trend/history/p/(.*)/v/(.*)/sig/(.*)/end/(.*)/'
        'duration/(.*)/steps/(.*)')

  def fetchSignatureHistory (self, parameters):
    if parameters['signature'] == '##null##':
      signatureCriterionPhrase = '          and signature is null'
    else:
      signatureCriterionPhrase = '          and signature = %(signature)s'
    if parameters['signature'] == '##empty##':
      parameters['signature'] = ''
    sql = """
      select
          CAST(ceil(EXTRACT(EPOCH FROM (window_end - %%(startDate)s)) / %%(stepSize)s) AS INT) as bucket_number,
          sum(count)
      from
          tcbs
      where
          %%(startDate)s < window_end
          and window_end <= %%(endDate)s
          and productdims_id = %%(productdims_id)s
          %s
      group by
          bucket_number
      order by
          1""" % signatureCriterionPhrase
    #logger.debug('%s', self.connection.cursor().mogrify(sql, parameters))
    return dict(((bucket, count) for bucket, count in db.execute(self.connection.cursor(), sql, parameters)))

  def signatureHistory (self, parameters, connection):
    self.connection = connection
    #logger.debug('signatureHistory %s  %s', parameters, self.connection)
    parameters.startDate = parameters.endDate - parameters.duration
    parameters.stepSize = dtutil.timeDeltaToSeconds(parameters.duration / parameters.steps)
    signatureHistory = self.fetchSignatureHistory(parameters)
    listOfEntries = []
    for bucket, total in self.fetchTotalsForRange(parameters):
      #logger.debug('signatureHistory fetchTotalsForRange %s  %s', bucket, total)
      d = { 'date': str(dt.timedelta(seconds=parameters.stepSize * bucket) + parameters.startDate),
            'count': signatureHistory.setdefault(bucket, 0),
            'percentOfTotal': signatureHistory.setdefault(bucket, 0) / float(total),
          }
      listOfEntries.append(d)
      #logger.debug(listOfEntries)
    result = { 'signatureHistory': listOfEntries,
               'signature': parameters.signature,
               'start_date': str(parameters.startDate),
               'end_date': str(parameters.endDate),
             }
    #logger.debug(result)
    return result
