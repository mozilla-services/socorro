import logging
logger = logging.getLogger("webapi")

import socorro.lib.util as util
import socorro.webapi.webapiService as webapi
import socorro.database.adu_codes as adu_codes
import socorro.database.database as db
import socorro.lib.datetimeutil as dtutil

#-----------------------------------------------------------------------------------------------------------------
def semicolonStringToListSanitized(aString):
  return [x.strip() for x in aString.replace("'","").split(';') if x.strip() != '']

#=================================================================================================================
class AduByDay(webapi.JsonServiceBase):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, configContext):
    super(AduByDay, self).__init__(configContext)
    self.connection = None


  #-----------------------------------------------------------------------------------------------------------------
  "/201005/adu/byday/p/{product}/v/{versions}/report_type/{report_type}/os/{os_names}/start/{start_date}/end/{end_date} "
  uri = '/201005/adu/byday/p/(.*)/v/(.*)/rt/(.*)/os/(.*)/start/(.*)/end/(.*)'
  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    convertedArgs = webapi.typeConversion([str, semicolonStringToListSanitized, str, semicolonStringToListSanitized, dtutil.datetimeFromISOdateString, dtutil.datetimeFromISOdateString], args)
    parameters = util.DotDict(zip(['product', 'listOfVersions', 'report_type', 'listOfOs_names',  'start_date', 'end_date'], convertedArgs))
    parameters.productdims_idList = [self.context['productVersionCache'].getId(parameters.product, x) for x in parameters.listOfVersions]
    self.connection = self.database.connection()
    try:
      return self.aduByDay(parameters)
    finally:
      self.connection.close()

  #-----------------------------------------------------------------------------------------------------------------
  def fetchAduHistory (self, parameters):
    if parameters.listOfOs_names and parameters.listOfOs_names != ['']:
      osNameListPhrase = (','.join("'%s'" % x for x in parameters.listOfOs_names)).replace('Mac', 'Mac OS X')
      parameters.os_phrase = "and os_name in (%s)" % osNameListPhrase
    else:
      parameters.os_phrase = ''
    sql = """
      select
          adu_date as date,
          substring(os_name, 1, 3) as product_os_platform,
          sum(adu_count)::BIGINT
      from
          product_adu pa
      join product_info pi using (product_version_id)
      where
          %%(start_date)s <= adu_date
          and adu_date <= %%(end_date)s
          and pi.product_name = %%(product)s
          and pi.version_string = %%(version)s
          %(os_phrase)s
      group by
          date,
          product_os_platform
      order by
          1""" % parameters
    #logger.debug('%s', self.connection.cursor().mogrify(sql.encode(self.connection.encoding), parameters))
    return dict((((date, os_name), count) for date, os_name, count in db.execute(self.connection.cursor(), sql, parameters)))

  #-----------------------------------------------------------------------------------------------------------------
  def fetchCrashHistory (self, parameters):
    if parameters.listOfOs_names and parameters.listOfOs_names != ['']:
      localOsList = [x[0:3] for x in parameters.listOfOs_names]
      osNameListPhrase = (','.join("'%s'" % x for x in localOsList))
      parameters.os_phrase = "os_short_name in (%s)" % osNameListPhrase
    else:
      parameters.os_phrase = '1=1'

    if parameters.report_type == 'crash':
      parameters.report_type_phrase = "report_type = '%s'" % adu_codes.CRASH_BROWSER
    elif parameters.report_type == 'hang':
      parameters.report_type_phrase = "report_type IN ('%s', '%s')" % (adu_codes.HANG_BROWSER, adu_codes.HANG_PLUGIN)
    else:
      # anything other than 'crash' or 'hang' will return all crashes
      # hang normalized are avoided so as not to count some hang ids multiple times
      parameters.report_type_phrase = "report_type IN ('%s', '%s', '%s', '%s')" % (
        adu_codes.CRASH_BROWSER,
        adu_codes.HANG_PLUGIN,
        adu_codes.CONTENT,
        adu_codes.OOP_PLUGIN,
      )

    sql = """
      SELECT adu_day::DATE, os_short_name, SUM(count)
      FROM daily_crashes
      WHERE timestamp without time zone %%(start_date)s <= adu_day AND
            adu_day <= timestamp without time zone %%(end_date)s AND
            productdims_id = %%(productdims_id)s AND
             %(os_phrase)s AND
             %(report_type_phrase)s
      GROUP BY adu_day, os_short_name
      order by
          1, 2""" % parameters
    #logger.debug('%s', self.connection.cursor().mogrify(sql.encode(self.connection.encoding), parameters))
    return dict((((bucket, os_name), count) for bucket, os_name, count in db.execute(self.connection.cursor(), sql, parameters)))

  #-----------------------------------------------------------------------------------------------------------------
  def combineAduCrashHistory (self, aduHistory, crashHistory):
    #print "adu ->", aduHistory
    #print "crash ->", crashHistory
    #print crashHistory.keys()

    result = []
    for aKey in sorted(crashHistory.keys()):
      row = util.DotDict()
      row.date = str(aKey[0])[:10]
      row.os = aKey[1]
      try:
        row.users = aduHistory[aKey]
      except KeyError:
        row.users = 0
      try:
        row.crashes = crashHistory[aKey]
      except KeyError:
        row.crashes = "unknown"
      result.append(row)
    return result


  #-----------------------------------------------------------------------------------------------------------------
  def aduByDay (self, parameters):
    #logger.debug('aduByDay %s  %s', parameters, self.connection)

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
      crashHistory = self.fetchCrashHistory(parameters)
      logger.info("CrashHistory=")
      logger.info(crashHistory)
      combinedAduCrashHistoryList = self.combineAduCrashHistory(aduHistory, crashHistory)
      logger.info("Combined Adu Crash History=")
      logger.info(combinedAduCrashHistoryList)
      singleVersionResult = { 'version': aVersion,
                              'statistics': combinedAduCrashHistoryList
                            }
      versionsResultData.append(singleVersionResult)
      #logger.debug(result)

    return result

class AduByDay200912(AduByDay):
  """ Deprecated Web Service, uses 201005 with report_type set to 'any' """
  def __init__(self, configContext):
    super(AduByDay200912, self).__init__(configContext)

  "/200912/adu/byday/p/{product}/v/{versions}/os/{os_names}/start/{start_date}/end/{end_date} "
  uri = '/200912/adu/byday/p/(.*)/v/(.*)/os/(.*)/start/(.*)/end/(.*)'

  def get(self, *args):
    logger.info("child get called %s" % str(args))
    return AduByDay.get(self, args[0], args[1], 'any', args[2],  args[3], args[4])
