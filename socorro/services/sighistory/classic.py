import datetime as dt
import urllib2 as u2
import logging
logger = logging.getLogger("webapi")

import socorro.lib.util as util
import socorro.webapi.webapiService as webapi
import socorro.database.database as db
import socorro.lib.datetimeutil as dtutil

#=================================================================================================================
class SignatureHistoryClassic(webapi.JsonServiceBase):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, configContext):
    super(SignatureHistoryClassic, self).__init__(configContext)
    logger.debug('SignatureHistoryClassic __init__')
  #-----------------------------------------------------------------------------------------------------------------
  uri = '/200911/topcrash/sig/trend/history/p/(.*)/v/(.*)/sig/(.*)/end/(.*)/duration/(.*)/steps/(.*)'
  #-----------------------------------------------------------------------------------------------------------------
  def fetchTotalsForRange(self, params):
    sql = """
      select
          CAST(ceil(EXTRACT(EPOCH FROM (window_end - %(startDate)s)) / %(stepSize)s) AS INT) as bucket_number,
          sum(count)
      from
          top_crashes_by_signature tcbs
      where
          %(startDate)s < window_end
          and window_end <= %(endDate)s
          and productdims_id = %(productdims_id)s
      group by
          bucket_number
      order by
          bucket_number"""
    return db.execute(self.connection.cursor(), sql, params)

  #-----------------------------------------------------------------------------------------------------------------
  def fetchSignatureHistory (self, params):
    if params['signature'] == '##null##':
      signatureCriterionPhrase = '          and signature is null'
    else:
      signatureCriterionPhrase = '          and signature = %(signature)s'
    if params['signature'] == '##empty##':
      params['signature'] = ''
    sql = """
      select
          CAST(ceil(EXTRACT(EPOCH FROM (window_end - %%(startDate)s)) / %%(stepSize)s) AS INT) as bucket_number,
          sum(count)
      from
          top_crashes_by_signature tcbs
      where
          %%(startDate)s < window_end
          and window_end <= %%(endDate)s
          and productdims_id = %%(productdims_id)s
          %s
      group by
          bucket_number
      order by
          1""" % signatureCriterionPhrase
    #logger.debug('%s', self.connection.cursor().mogrify(sql, params))
    return dict(((bucket, count) for bucket, count in db.execute(self.connection.cursor(), sql, params)))

  #-----------------------------------------------------------------------------------------------------------------
  def signatureHistory (self, params, connection):
    self.connection = connection
    params.productdims_id = (self.context['productVersionCache']
                                     .getId(params.product,
                                            params.version))
    #logger.debug('signatureHistory %s  %s', params, self.connection)
    params.startDate = params.endDate - params.duration
    params.stepSize = dtutil.timeDeltaToSeconds(params.duration /
                                                    params.steps)
    signatureHistory = self.fetchSignatureHistory(params)
    listOfEntries = []
    for bucket, total in self.fetchTotalsForRange(params):
      #logger.debug('signatureHistory fetchTotalsForRange %s  %s', bucket, total)
      d = { 'date': str(dt.timedelta(seconds=params.stepSize * bucket) + params.startDate),
            'count': signatureHistory.setdefault(bucket, 0),
            'percentOfTotal': signatureHistory.setdefault(bucket, 0) / float(total),
          }
      listOfEntries.append(d)
      #logger.debug(listOfEntries)
    result = { 'signatureHistory': listOfEntries,
               'signature': params.signature,
               'start_date': str(params.startDate),
               'end_date': str(params.endDate),
             }
    #logger.debug(result)
    return result
