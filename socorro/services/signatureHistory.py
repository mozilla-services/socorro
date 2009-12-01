import datetime as dt
import urllib2 as u2
import logging
logger = logging.getLogger("webapi")

import socorro.lib.util as util
import socorro.webapi.webapiService as webapi
import socorro.lib.psycopghelper as psy
import socorro.lib.datetimeutil as dtutil

#=================================================================================================================
class SignatureHistory(webapi.JsonServiceBase):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, configContext):
    super(SignatureHistory, self).__init__(configContext)
    logger.debug('SignatureHistory __init__')
  #-----------------------------------------------------------------------------------------------------------------
  uri = '/200911/topcrash/sig/trend/history/p/(.*)/v/(.*)/sig/(.*)/end/(.*)/duration/(.*)/steps/(.*)'
  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    logger.debug('SignatureHistory get %s', args)
    convertedArgs = webapi.typeConversion([str, str, u2.unquote, dtutil.datetimeFromISOdateString, dtutil.strHoursToTimeDelta, int], args)
    parameters = util.DotDict(zip(['product','version', 'signature', 'endDate','duration', 'steps'], convertedArgs))
    logger.debug("SignatureHistory %s", parameters)
    try:
      self.connection, self.cursor = self.connectionPool.connectToDatabase()
      logger.debug('connection: %s', self.connection)
      return self.signatureHistory(parameters)
    finally:
      self.connection.close()

  #-----------------------------------------------------------------------------------------------------------------
  def fetchTotalsForRange(self, parameters):
    sql = """
      select
          CAST(ceil(EXTRACT(EPOCH FROM (window_end - %(startDate)s)) / %(stepSize)s) AS INT) as bucket_number,
          sum(count)
      from
          top_crashes_by_signature tcbs
      where
          %(startDate)s < window_end
          and window_end <= %(endDate)s
      group by
          bucket_number
      order by
          bucket_number"""
    return psy.execute(self.connection.cursor(), sql, parameters)

  #-----------------------------------------------------------------------------------------------------------------
  def fetchSignatureHistory (self, parameters):
    sql = """
      select
          CAST(ceil(EXTRACT(EPOCH FROM (window_end - %(startDate)s)) / %(stepSize)s) AS INT) as bucket_number,
          sum(count)
      from
          top_crashes_by_signature tcbs
      where
          %(startDate)s < window_end
          and window_end <= %(endDate)s
          and signature = %(signature)s
      group by
          bucket_number
      order by
          1"""
    return dict(((bucket, count) for bucket, count in psy.execute(self.connection.cursor(), sql, parameters)))

  #-----------------------------------------------------------------------------------------------------------------
  def signatureHistory (self, parameters):
    logger.debug('signatureHistory %s  %s', parameters, self.connection)
    #listOfEntries = [{ 'date': somedate,
                      #'count': somecount,
                      #'percentOfTotal': somepercent
                    #},]
    parameters.startDate = parameters.endDate - parameters.duration
    parameters.stepSize = dtutil.timeDeltaToSeconds(parameters.duration / parameters.steps)
    signatureHistory = self.fetchSignatureHistory(parameters)
    listOfEntries = []
    for bucket, total in self.fetchTotalsForRange(parameters):
      logger.debug('signatureHistory fetchTotalsForRange %s  %s', bucket, total)
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
    logger.debug(result)
    return result