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

import psycopg2
import psycopg2.extras

import socorro.lib.util


def update(configContext, logger):
  serverStatsSql = """INSERT INTO server_status
  (date_recently_completed, date_oldest_job_queued, avg_process_sec,
   avg_wait_sec, waiting_job_count, processors_count, date_created)
 SELECT

  (SELECT MAX(jobs.completeddatetime)
   FROM jobs WHERE jobs.completeddatetime IS NOT NULL) AS date_recently_completed,

  (SELECT jobs.queueddatetime
   FROM jobs WHERE jobs.completeddatetime IS NULL
   ORDER BY jobs.queueddatetime LIMIT 1) AS date_oldest_job_queued,

  (SELECT COALESCE (
     EXTRACT (EPOCH FROM avg(jobs.completeddatetime - jobs.starteddatetime)),
     0) FROM jobs
   WHERE jobs.completeddatetime > %s) AS avg_process_sec ,

  (SELECT COALESCE (
     EXTRACT (EPOCH FROM avg(jobs.completeddatetime - jobs.queueddatetime)),
     0) FROM jobs
   WHERE jobs.completeddatetime > %s) AS avg_wait_sec,

  (SELECT COUNT(jobs.id)
   FROM jobs WHERE jobs.completeddatetime IS NULL) AS waiting_job_count,

  (SELECT count(processors.id)
   FROM processors ) AS processors_count,

  CURRENT_TIMESTAMP AS date_created;"""


  serverStatsLastUpdSql = """ /* serverstatus.lastUpd */
SELECT id, date_recently_completed, date_oldest_job_queued, avg_process_sec,
        avg_wait_sec, waiting_job_count, processors_count, date_created
FROM server_status ORDER BY date_created DESC LIMIT 1;
"""

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
    cur.execute(serverStatsSql, (startTime, startTime))
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
