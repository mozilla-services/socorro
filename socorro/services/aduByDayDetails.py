import logging
logger = logging.getLogger("webapi")

import socorro.lib.util as util
import socorro.webapi.webapiService as webapi
import socorro.database.adu_codes as adu_codes
import socorro.database.database as db
import socorro.lib.datetimeutil as dtutil
from socorro.services.aduByDay import semicolonStringToListSanitized
from socorro.services.aduByDay import AduByDay as AduByDayBase

#=================================================================================================================
class AduByDayDetails(AduByDayBase):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, configContext):
    super(AduByDayDetails, self).__init__(configContext)
    self.connection = None

  #-----------------------------------------------------------------------------------------------------------------
  "/201006/adu/byday/details/p/{product}/v/{versions}/rt/{report_types}/os/{os_names}/start/{start_date}/end/{end_date} "
  uri = '/201006/adu/byday/details/p/(.*)/v/(.*)/rt/(.*)/os/(.*)/start/(.*)/end/(.*)'
  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    convertedArgs = webapi.typeConversion([str, semicolonStringToListSanitized, semicolonStringToListSanitized, semicolonStringToListSanitized, dtutil.datetimeFromISOdateString, dtutil.datetimeFromISOdateString], args)
    parameters = util.DotDict(zip(['product', 'listOfVersions', 'listOfReport_types', 'listOfOs_names',  'start_date', 'end_date'], convertedArgs))
    parameters.productdims_idList = [self.context.productVersionCache.getId(parameters.product, x) for x in parameters.listOfVersions]
    self.connection = self.database.connection()
    try:
      return self.aduByDayDetails(parameters)
    finally:
      self.connection.close()

  #-----------------------------------------------------------------------------------------------------------------
  def fetchCrashHistoryDetails (self, parameters):
    if parameters.listOfOs_names and parameters.listOfOs_names != ['']:
      localOsList = [x[0:3] for x in parameters.listOfOs_names]
      osNameListPhrase = (','.join("'%s'" % x for x in localOsList))
      parameters.os_phrase = "os_short_name in (%s)" % osNameListPhrase
    else:
      parameters.os_phrase = '1=1'

    if parameters.listOfReport_types and parameters.listOfReport_types != ['']:
      lookup = {'crash':        adu_codes.CRASH_BROWSER,
                'oopp':         adu_codes.OOP_PLUGIN,
                'hang_unique':  adu_codes.HANGS_NORMALIZED,
                'hang_browser': adu_codes.HANG_BROWSER,
                'hang_plugin':  adu_codes.HANG_PLUGIN,
                }
      reportTypeListPhrase = (','.join("'%s'" % lookup[x] for x in parameters.listOfReport_types))
      parameters.report_types_phrase = "report_type in (%s)" % reportTypeListPhrase
    else:
      parameters.report_types_phrase = '1=1'

    columnSql = "SUM(CASE WHEN report_type = '%s' THEN count ELSE 0 END) as %s"
    parameters.selectListPhrase = (', '.join((columnSql % (lookup[x], x)) for x in parameters.listOfReport_types))

    sql = """
      SELECT adu_day, os_short_name, %(selectListPhrase)s
      FROM daily_crashes
      WHERE timestamp without time zone %%(start_date)s < adu_day AND
            adu_day <= timestamp without time zone %%(end_date)s AND
            productdims_id = %%(productdims_id)s AND
             %(os_phrase)s AND
             %(report_types_phrase)s
      GROUP BY adu_day, os_short_name
      order by
          1, 2""" % parameters
    #logger.debug('%s', self.connection.cursor().mogrify(sql.encode(self.connection.encoding), parameters))
    db_results = db.execute(self.connection.cursor(), sql, parameters)
    column_names = ('date', 'os') + tuple(parameters.listOfReport_types)

    structure = [dict(zip(column_names, x)) for x in db_results]
    structures = dict([((x['date'], x['os']), x) for x in structure])
    return structures

  #-----------------------------------------------------------------------------------------------------------------
  def combineAduCrashHistory (self, aduHistory, crashHistory):
    """ adu   -> {(datetime.datetime(2010, 6, 1, 0, 0), 'Lin'): 4601L
        crash -> {(datetime.datetime(2010, 6, 2, 0, 0), 'Lin'): 1L,
        new crash history
        crash -> {'adu_day': datetime.datetime(2010...), 'os_short_name': 'Lin'): {
        produces
        {'os': 'Win', 'date': '3010-3432', 'crashes':
    """
    result = []
    for aKey in sorted(crashHistory.keys()):
      crashHistory[aKey]['date'] = str(aKey[0])[:10]
      try:
        crashHistory[aKey]['users'] = aduHistory[aKey]
      except KeyError:
        crashHistory[aKey]['users'] = 0
      result.append(crashHistory[aKey])
    return result


  #-----------------------------------------------------------------------------------------------------------------
  def aduByDayDetails (self, parameters):
    versionsResultData = []
    result = { 'product': parameters.product,
               'start_date': str(parameters.start_date),
               'end_date': str(parameters.end_date),
               'versions': versionsResultData,
             }
    for aVersion, aProductDimsId in zip(parameters.listOfVersions, parameters.productdims_idList):
      parameters.version = aVersion
      parameters.productdims_id = aProductDimsId
      aduHistory = self.fetchAduHistory(parameters)
      crashHistory = self.fetchCrashHistoryDetails(parameters)
      combinedAduCrashHistoryList = self.combineAduCrashHistory(aduHistory, crashHistory)
      singleVersionResult = { 'version': aVersion,
                              'statistics': combinedAduCrashHistoryList
                            }
      versionsResultData.append(singleVersionResult)
    return result
