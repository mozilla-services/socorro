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

  def fetchSigHistory(self, parameters):
    if parameters['signature'] == '##null##':
      signatureCriterionPhrase = '          and signature is null'
    else:
      signatureCriterionPhrase = '          and signature = %(signature)s'
    if parameters['signature'] == '##empty##':
      parameters['signature'] = ''
    sql = """
      WITH hist as (
      select
          report_date,
          report_count
      from
          tcbs join signatures using (signature_id)
               join product_versions using (product_version_id)
      where
          report_date between %%(startDate)s and %%(endDate)s
          and product_name = %%(product)s
          and version_string = %%(version)s
          %s
      group by
          report_date, report_count
      order by 1),
      scaling_window AS (
          select 
              hist.*,
              sum(report_count) over () as total_crashes
          from 
              hist
      )
      SELECT 
          report_date,
          report_count,
          report_count / total_crashes::float as percent_of_total
      from scaling_window
      order by report_date DESC
    """ % signatureCriterionPhrase
    #logger.debug('%s', self.connection.cursor().mogrify(sql, parameters))
    return db.execute(self.connection.cursor(), sql, parameters)


  def signatureHistory (self, parameters, connection):
    self.connection = connection
    #logger.debug('signatureHistory %s  %s', parameters, self.connection)
    parameters.startDate = parameters.endDate - parameters.duration
    parameters.stepSize = dtutil.timeDeltaToSeconds(parameters.duration / parameters.steps)
    listOfEntries = []
    for date, count, percent in self.fetchSigHistory(parameters):
      #logger.debug('signatureHistory fetchTotalsForRange %s  %s', bucket, total)
      d = { 'date': date.isoformat(),
            'count': count,
            'percentOfTotal': percent,
          }
      listOfEntries.append(d)
      #logger.debug(listOfEntries)
    result = { 'signatureHistory': listOfEntries,
               'signature': parameters.signature,
               'start_date': parameters.startDate.isoformat(),
               'end_date': parameters.endDate.isoformat(),
             }
    #logger.debug(result)
    return result
