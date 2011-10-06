import logging
logger = logging.getLogger("webapi")

import socorro.database.database as db
import socorro.webapi.webapiService as webapi
import socorro.lib.util as util
import socorro.lib.datetimeutil as dtutil

class HangReport(webapi.JsonServiceBase):
  def __init__(self, configContext):
    super(HangReport, self).__init__(configContext)
    logger.debug('HangReport __init__')

  # http://socorro-api/bpapi/201109/reports/hang/p/Firefox/v/9.0a1/end/2011-09-20T15%3A00%3A00T%2B0000/days/1/listsize/300
  uri = '/201109/reports/hang/p/(.*)/v/(.*)/end/(.*)/duration/(.*)/listsize/(.*)'

  def get(self, *args):
    convertedArgs = webapi.typeConversion([str, str, dtutil.datetimeFromISOdateString, int, int], args)
    parameters = util.DotDict(zip(['product', 'version', 'end', 'duration', 'listsize'], convertedArgs))

    connection = self.database.connection()
    cursor = connection.cursor()

    hangReport = """
          /* socorro.services.HangReport */
          SELECT browser_signature, plugin_signature, 
                 browser_hangid, flash_version, url,
                 uuid, duplicates, report_day
          FROM hang_report
          WHERE product = %(product)s
          AND version = %(version)s
          AND report_day > utc_day_begins_pacific(((%(end)s)::timestamp - interval '%(duration)s days')::date)
          LIMIT %(listsize)s"""
  
    logger.debug(cursor.mogrify(hangReport, parameters))
    cursor.execute(hangReport, parameters)

    result = []
    for row in cursor.fetchall():
      (browser_signature, plugin_signature, browser_hangid, flash_version,
       url, uuid, duplicates, report_day) = row
      result.append({'browser_signature': browser_signature,
                     'plugin_signature': plugin_signature,
                     'browser_hangid': browser_hangid,
                     'flash_version': flash_version,
                     'url': url,
                     'uuid': uuid,
                     'duplicates': duplicates,
                     'report_day': str(report_day)})
    return {'hangReport': result, 'end_date': str(parameters['end'])}
