#!/usr/bin/python

"""
This script is what populates the aggregate server_status table for jobs and processors.

It provides up to date reports on the status of Socorro servers

The following fields are updated in server_status table:
  id - primary key
  date_recently_completed - timestamp for job most recently processed in jobs table
  date_oldest_job_queued - timestamp for the oldest job which is incomplete
  avg_process_sec - Average number of seconds (float) for jobs completed since last run
                    or 0.0 in edge case where no jobs have been processed
  avg_wait_sec- Average number of seconds (float) for jobs completed since last run
                or 0.0 in edge case where no jobs have been processed
  waiting_job_count - Number of jobs incomplete in queue
  processors_count - Number of processors running to process jobs
  date_created - timestamp for this record being udpated
"""
import time
import datetime
import json
import urllib2

import psycopg2
import psycopg2.extras

import socorro.lib.util
import socorro.webapi.webapiService as webapi


def update(configContext, logger):
  serverStatsSql = """
    INSERT INTO server_status 
    (date_recently_completed, date_oldest_job_queued, avg_process_sec,  
     avg_wait_sec, waiting_job_count, processors_count, date_created) 
     VALUES
     (%s, %s, %s,
     %s, %s, %s, CURRENT_TIMESTAMP);"""

  serverStatsLastUpdSql = """ /* serverstatus.lastUpd */
    SELECT id, date_recently_completed, date_oldest_job_queued, avg_process_sec, 
            avg_wait_sec, waiting_job_count, processors_count, date_created 
    FROM server_status ORDER BY date_created DESC LIMIT 1;
    """

  # get the data from the API status call
  statusURL = "http://%s%s" %  (configContext.webservicesHostPort, '/status')

  try:
    statusResponse = urllib2.urlopen(statusURL)
    status = json.loads(statusResponse.read())
  except Exception, e:
    socorro.lib.util.reportExceptionAndAbort(logger)

  try:
    databaseDSN = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % configContext
    conn = psycopg2.connect(databaseDSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
  except:
    socorro.lib.util.reportExceptionAndAbort(logger)

  startTime = datetime.datetime.now() 
  startTime -= configContext.processingInterval
  timeInserting = 0
  if configContext.debug:
    logger.debug("Creating stats from now back until %s" % startTime)
  try:
    before = time.time()
    cur.execute(serverStatsSql, (status['recently_completed'], 
                                 status['oldest_active_report'], 
                                 status['average_time_to_process'],
                                 status['total_time_for_processing'], 
                                 status['active_raw_reports_in_queue'], 
                                 status['processors_running']))
    timeInserting = time.time() - before;
    cur.execute(serverStatsLastUpdSql)
    row = cur.fetchone()
    conn.commit()
  except:
    socorro.lib.util.reportExceptionAndAbort(logger)

  if row:
    logger.info("Server Status id=%d was updated at %s -- recent=%s, oldest=%s, avg_proc=%s, avg_wait=%s, waiting=%s, procs=%s -- in %s seconds" % (row['id'], row['date_created'], row['date_recently_completed'], row['date_oldest_job_queued'], row['avg_process_sec'], row['avg_wait_sec'], row['waiting_job_count'], row['processors_count'], timeInserting))
  else:
    msg = "Unable to read from server_status table after attempting to insert a new record"
    logger.warn(msg)
    raise Exception(msg)
