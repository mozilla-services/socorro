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

  # http://socorro-api/bpapi/201109/reports/hang/p/Firefox/v/9.0a1/end/2011-09-20T15%3A00%3A00T%2B0000/days/1/listsize/300/page/1
  uri = '/201109/reports/hang/p/(.*)/v/(.*)/end/(.*)/duration/(.*)/listsize/(.*)/page/(.*)'

  def get(self, *args):
    convertedArgs = webapi.typeConversion([str, str, dtutil.datetimeFromISOdateString, int, int, int], args)
    parameters = util.DotDict(zip(['product', 'version', 'end', 'duration', 'listsize', 'page'], convertedArgs))

    connection = self.database.connection()
    cursor = connection.cursor()

    hangReportCountSql = """
          /* socorro.services.HangReportCount */
          SELECT count(*)
          FROM hang_report
          WHERE product = %(product)s
          AND version = %(version)s
          AND date_processed > utc_day_begins_pacific(((%(end)s)::timestamp - interval '%(duration)s days')::date)
    """

    logger.debug(cursor.mogrify(hangReportCountSql, parameters))
    cursor.execute(hangReportCountSql, parameters)

    hangReportCount = cursor.fetchone()[0]

    listsize = parameters['listsize']
    page = parameters['page']
    totalPages = hangReportCount / listsize
    logger.debug('total pages: %s' % totalPages)

    parameters['offset'] = listsize * (page - 1)

    hangReportSql = """
          /* socorro.services.HangReport */
          SELECT browser_signature, plugin_signature, 
                 browser_hangid, flash_version, url,
                 uuid, duplicates, date_processed
          FROM hang_report
          WHERE product = %(product)s
          AND version = %(version)s
          AND date_processed > utc_day_begins_pacific(((%(end)s)::timestamp - interval '%(duration)s days')::date)
          LIMIT %(listsize)s
          OFFSET %(offset)s
          ORDER BY date_processed"""
  
    logger.debug(cursor.mogrify(hangReportSql, parameters))
    cursor.execute(hangReportSql, parameters)

    result = []
    for row in cursor.fetchall():
      (browser_signature, plugin_signature, browser_hangid, flash_version,
       url, uuid, duplicates, date_processed) = row
      result.append({'browser_signature': browser_signature,
                     'plugin_signature': plugin_signature,
                     'browser_hangid': browser_hangid,
                     'flash_version': flash_version,
                     'url': url,
                     'uuid': uuid,
                     'duplicates': duplicates,
                     'date_processed': str(date_processed)})
    return {'hangReport': result, 'endDate': str(parameters['end']), 'totalPages': totalPages, 'currentPage': page,
            'totalCount': hangReportCount}
