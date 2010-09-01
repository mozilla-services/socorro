import datetime as dt
import json
import urllib2
import logging
logger = logging.getLogger("webapi")

import socorro.lib.util as sutil
import socorro.registrar.registrar as sreg
import socorro.webapi.webapiService as webapi
import socorro.storage.crashstorage as cstore 

# Report status for the webapp to use at /status

#===============================================================================
class Status(webapi.JsonServiceBase):

  #-----------------------------------------------------------------------------
  def __init__(self, context):
    super(Status, self).__init__(context)

    self.registrarListProcessorsURL =  "http://%s%s" % (self.context.registrationHostPort,
                                                        sreg.ListService.uri)
    self.registrarProcessorStatsURL =  "http://%s%s" % (self.context.registrationHostPort,
                                                        #sreg.ProcessorStatsService.uri)
                                                        '/201008/stats/')

    self.crashStoragePool = cstore.CrashStoragePool(self.context)

  
  #-----------------------------------------------------------------------------
  "/status"
  uri = '/status'
  #uriArgNames = []
  #uriArgTypes = []
  #uriDoc = "Returns JSON containing status info from processors and HBase"
  #-----------------------------------------------------------------------------
  def get(self, *args):
    now = dt.datetime.now()

    # get active processors from the registrar
    processors = 0
    try:
      processorListResponse = urllib2.urlopen(self.registrarListProcessorsURL)
      processors = json.loads(processorListResponse.read())
    except urllib2.URLError, e:
      sutil.reportExceptionAndContinue(self.logger,
                                       loggingLevel=logging.DEBUG,
                                       showTraceback=True)

    # get processor stats from the registrar
    mostRecent = 0
    processTime = 0
    try:
      processTimeResponse = urllib2.urlopen(self.registrarProcessorStatsURL + 'processTime')
      processTime = json.loads(processTimeResponse.read())
      mostRecentResponse = urllib2.urlopen(self.registrarProcessorStatsURL + 'mostRecent')
      mostRecent = json.loads(mostRecentResponse.read())
      totalTimeForProcessingResponse = urllib2.urlopen(self.registrarProcessorStatsURL + 'totalTimeForProcessing')
      totalTimeForProcessing = json.loads(totalTimeForProcessingResponse.read())
    except urllib2.URLError, e:
      sutil.reportExceptionAndAbort(self.logger)

    # get queue stats from HBase
    try:
      crashStorage = self.crashStoragePool.crashStorage()
      queueStats = crashStorage.hbaseConnection.get_queue_statistics()
    except Exception, x:
      sutil.reportExceptionAndAbort(self.logger)
      
    # fill in data
    status =  { 'time_called': str(now), 
                'processors_running': len(processors),                
                'average_time_to_process': processTime,               
                'recently_completed': mostRecent,                     
                'total_time_for_processing': totalTimeForProcessing,                     
                'active_raw_reports_in_queue': queueStats['active_raw_reports_in_queue'],            
                'oldest_active_report': queueStats['oldest_active_report'],
                'processed_reports_in_dbfeeder_queue': queueStats['processed_reports_in_dbfeeder_queue'],
                'throttled_raw_reports_in_queue': queueStats['throttled_raw_reports_in_queue'],               
                'priority_processed_reports_in_dbfeeder_queue': queueStats['priority_processed_reports_in_dbfeeder_queue'],
                'priority_raw_reports_in_queue': queueStats['priority_raw_reports_in_queue'],
                'oldest_processed_report': queueStats['oldest_processed_report'],                       
                'oldest_active_report': queueStats['oldest_active_report'],                       
                'oldest_throttled_report': queueStats['oldest_throttled_report'],                       
              } 

    return status 
