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
  "/adu/byday/details/p/{product}/v/{versions}/rt/{report_types}/os/{os_names}/start/{start_date}/end/{end_date} "
  uri = '/adu/byday/details/p/(.*)/v/(.*)/rt/(.*)/os/(.*)/start/(.*)/end/(.*)'
  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    convertedArgs = webapi.typeConversion([str, semicolonStringToListSanitized, semicolonStringToListSanitized, semicolonStringToListSanitized, dtutil.string_to_datetime, dtutil.string_to_datetime], args)
    parameters = util.DotDict(zip(['product', 'listOfVersions', 'listOfReport_types', 'listOfOs_names',  'start_date', 'end_date'], convertedArgs))
    parameters.productdims_idList = [self.context['productVersionCache'].getId(parameters.product, x) for x in parameters.listOfVersions]
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
    logger.debug("created phrase %s" % parameters.selectListPhrase)
    sql = """
      SELECT adu_day, os_short_name, %(selectListPhrase)s
      FROM daily_crashes
      WHERE timestamp with time zone %%(start_date)s < adu_day AND
            adu_day <= timestamp with time zone %%(end_date)s AND
            productdims_id = %%(productdims_id)s AND
             %(os_phrase)s AND
             %(report_types_phrase)s
      GROUP BY adu_day, os_short_name
      order by
          1, 2""" % parameters
    logger.debug('%s', self.connection.cursor().mogrify(sql.encode(self.connection.encoding), parameters))
    db_results = db.execute(self.connection.cursor(), sql, parameters)
    # idea... we could do {'crash': crash, 'hang_plugin': hang_plugin}... etc building this dict up above
    #return dict((((bucket, os_name), crash) for bucket, os_name, crash, hang_plugin in db_results))
    column_names = ('date', 'os') + tuple(parameters.listOfReport_types)
    # grab bucket value and os_name value, rest go into (('hang_plugin': 3), ...)

    structure = [dict(zip(column_names, x)) for x in db_results]
    structures = dict([((x['date'], x['os']), x) for x in structure])
    # [[('adu_by_day', date), ('os_short_name', 'Win'),...],
    #  [...]]
    # ultimately we want to produce [(date, os): {'date':date, 'os': "Lin", 'users': 234, 'crashes': 234]
    # so we can do an quick lookup by (date, os)
    logger.info("Wow, structure=")
    logger.info(structures)
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
      # aKey is a (date, os_name)

      #row = util.DotDict()
      #row.date = str(aKey[0])[:10]
      crashHistory[aKey]['date'] = str(aKey[0])[:10]
      #row.os = aKey[1]
      try:
        #row.users = aduHistory[aKey]
        crashHistory[aKey]['users'] = aduHistory[aKey]
      except KeyError:
        #row.users = 0
        crashHistory[aKey]['users'] = 0
      """try:
        row.crashes = crashHistory[aKey]
      except KeyError:
        row.crashes = "unknown" """
      #result.append(row)
      result.append(crashHistory[aKey])
    return result


  #-----------------------------------------------------------------------------------------------------------------
  def aduByDayDetails (self, parameters):
    logger.debug('aduByDayDetails %s  %s', parameters, self.connection)
    # TODO test with no report_types
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
      logger.info("CrashHistory=")
      logger.info(crashHistory)
      combinedAduCrashHistoryList = self.combineAduCrashHistory(aduHistory, crashHistory)
      #  [{'date': '2010-06-02', 'os': 'Lin', 'users': 4779L, 'crashes': 1L},
      logger.info("Combined Adu Crash History=")
      logger.info(combinedAduCrashHistoryList)
      singleVersionResult = { 'version': aVersion,
                              'statistics': combinedAduCrashHistoryList
                            }
      versionsResultData.append(singleVersionResult)
      #logger.debug(result)

    return result
