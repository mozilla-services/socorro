import datetime as dt
import urllib2 as u2
import logging
logger = logging.getLogger("webapi")

import socorro.lib.util as util
import socorro.webapi.webapiService as webapi
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
    logger.debug('aduHistory __init__')
  #-----------------------------------------------------------------------------------------------------------------
  "/200912/adu/byday/p/{product}/v/{versions}/os/{os_names}/start/{start_date}/end/{end_date} "
  uri = '/200912/adu/byday/p/(.*)/v/(.*)/os/(.*)/start/(.*)/end/(.*)'
  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    convertedArgs = webapi.typeConversion([str, semicolonStringToListSanitized, semicolonStringToListSanitized, dtutil.datetimeFromISOdateString, dtutil.datetimeFromISOdateString], args)
    parameters = util.DotDict(zip(['product','listOfVersions', 'listOfOs_names', 'start_date', 'end_date'], convertedArgs))
    parameters.productdims_idList = [self.context['productVersionCache'].getId(parameters.product, x) for x in parameters.listOfVersions]
    logger.debug("AduByDay get %s", parameters)
    self.connection = self.database.connection()
    #logger.debug('connection: %s', self.connection)
    try:
      return self.aduByDay(parameters)
    finally:
      self.connection.close()

  #-----------------------------------------------------------------------------------------------------------------
  def fetchAduHistory (self, parameters):
    if parameters.listOfOs_names and parameters.listOfOs_names != ['']:
      osNameListPhrase = (','.join("'%s'" % x for x in parameters.listOfOs_names)).replace('Mac', 'Mac OS/X')
      parameters.os_phrase = "and product_os_platform in (%s)" % osNameListPhrase
    else:
      parameters.os_phrase = ''
    sql = """
      select
          date,
          case when product_os_platform = 'Mac OS/X' then
            'Mac'
          else
            product_os_platform
          end as product_os_platform,
          sum(adu_count)
      from
          raw_adu ra
      where
          %%(start_date)s <= date
          and date <= %%(end_date)s
          and product_name = %%(product)s
          and product_version = %%(version)s
          %(os_phrase)s
      group by
          date,
          product_os_platform
      order by
          1""" % parameters
    #logger.debug('%s', self.connection.cursor().mogrify(sql, parameters))
    return dict((((date, os_name), count) for date, os_name, count in db.execute(self.connection.cursor(), sql, parameters)))

  #-----------------------------------------------------------------------------------------------------------------
  def fetchCrashHistory (self, parameters):
    if parameters.listOfOs_names and parameters.listOfOs_names != ['']:
      localOsList = [x for x in parameters.listOfOs_names]
      if 'Windows' in localOsList:
        localOsList.append('Windows NT')
      osNameListPhrase = (','.join("'%s'" % x for x in localOsList)).replace('Mac', 'Mac OS X')
      parameters.os_phrase = "and os.os_name in (%s)" % osNameListPhrase
    else:
      parameters.os_phrase = '--'
    sql = """
      select
          CAST(ceil(EXTRACT(EPOCH FROM (window_end - timestamp without time zone %%(start_date)s - interval %%(socorroTimeToUTCInterval)s)) / 86400) AS INT) * interval '24 hours' + timestamp without time zone %%(start_date)s as day,
          case when os.os_name = 'Windows NT' then
            'Windows'
          when os.os_name = 'Mac OS X' then
            'Mac'
          else
            os.os_name
          end as os_name,
          sum(count)
      from
          top_crashes_by_signature tcbs
              join osdims os on tcbs.osdims_id = os.id
                  %(os_phrase)s
      where
          (timestamp without time zone %%(start_date)s - interval %%(socorroTimeToUTCInterval)s) < window_end
          and window_end <= (timestamp without time zone %%(end_date)s - interval %%(socorroTimeToUTCInterval)s)
          and productdims_id = %%(productdims_id)s
      group by
          day,
          os_name
      order by
          1, 2""" % parameters
    #logger.debug('%s', self.connection.cursor().mogrify(sql, parameters))
    return dict((((bucket, os_name), count) for bucket, os_name, count in db.execute(self.connection.cursor(), sql, parameters)))

  #-----------------------------------------------------------------------------------------------------------------
  def combineAduCrashHistory (self, aduHistory, crashHistory):
    #print "adu ->", aduHistory
    #print "crash ->", crashHistory
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
    parameters.stepSize = 24 * 60 * 60 # number of seconds in 24 hours for the crash history query
    parameters.socorroTimeToUTCInterval = '8 hours'
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
      combinedAduCrashHistoryList = self.combineAduCrashHistory(aduHistory, crashHistory)
      singleVersionResult = { 'version': aVersion,
                              'statistics': combinedAduCrashHistoryList
                            }
      versionsResultData.append(singleVersionResult)
      #logger.debug(result)

    return result