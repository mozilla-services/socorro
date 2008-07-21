#!/usr/bin/python

"""
This script is what populates the aggregate summary table for crash dump reports.
It lets us efficiently provide up to date reports on the crash dump data.
Examples of these reports are the Top 100 crashers, All Time Crashers, New Crashers
"""
import sys
import logging
import logging.handlers
from operator import itemgetter
import time
import datetime

import psycopg2
import psycopg2.extras

import topcrashes_config as config
import socorro.lib.ConfigurationManager as configurationManager

import socorro.lib.util


def calc_tots(crashes, crash_count):
  """ Calculate the total number of crashes per signature combo, as well as uptime averages. """
  for pvCombo, data in crashes.items():
    for signature, signatureData in crashes[pvCombo].items():
      fullKey = (pvCombo[0], pvCombo[1], pvCombo[2], signature)
      signatureData['total'] = signatureData['win'] + signatureData['mac'] + signatureData['lin']
      signatureData['uptime_average'] = signatureData['uptime'] / crash_count[fullKey]
  
  if configContext.debug:
    for pvCombo, data in crashes.items():
      for signature, signatureData in crashes[pvCombo].items():
        logger.debug("%s Total: %d" % ((pvCombo, signature), signatureData['total']))
        logger.debug("%s Uptime Average: %d" % ((pvCombo, signature), signatureData['uptime_average']))
    
def calc_ranks(crashes):
  """ Calculate the new ranks of the crashes, by total number of crashes """
  ranks = []
   
  for signature, signatureData in crashes.items():
    ranks.append([signature, signatureData['total']])
  
  ranks = sorted(ranks, key=itemgetter(1))
  ranks.reverse()
  
  for rank in range(0, len(ranks)):
    crashes[ranks[rank][0]]['rank'] = rank + 1
  
  if configContext.debug:
    for signature, data in crashes.items():
      logger.debug("%s is ranked at: %d" % (signature, crashes[signature]['rank']))

try:
  configContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Top Crashes Summary")
except configurationManager.NotAnOptionError, x:
  print >>sys.stderr, x
  print >>sys.stderr, "for usage, try --help"
  sys.exit(1)

logger = logging.getLogger("topcrashes_summary")
logger.setLevel(logging.DEBUG)

stderrLog = logging.StreamHandler()
stderrLog.setLevel(configContext.stderrErrorLoggingLevel)
stderrLogFormatter = logging.Formatter(configContext.stderrLineFormatString)
stderrLog.setFormatter(stderrLogFormatter)
logger.addHandler(stderrLog)

rotatingFileLog = logging.handlers.RotatingFileHandler(configContext.logFilePathname, "a", configContext.logFileMaximumSize, configContext.logFileMaximumBackupHistory)
rotatingFileLog.setLevel(logging.DEBUG)
rotatingFileLogFormatter = logging.Formatter(configContext.logFileLineFormatString)
rotatingFileLog.setFormatter(rotatingFileLogFormatter)
logger.addHandler(rotatingFileLog)

summary_crashes = {}
crash_count = {}

try:
  conn = psycopg2.connect(configContext.databaseDSN)
  cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
except:
  socorro.lib.util.reportExceptionAndAbort(logger)


columns = ["product", "version", "build", "signature", "uptime", "os_name", "user_id"]

start_time = datetime.datetime.now()
end_time = datetime.datetime.now()
now = datetime.datetime.now()
p_interval = datetime.timedelta(seconds=configContext.processingInterval)
initModeDate = now - datetime.timedelta(days=14)

if not configContext.initMode:
  startsql = "SELECT last_updated FROM topcrashers ORDER BY last_updated DESC LIMIT 1"
  try:
    cur.execute(startsql)
    row = cur.fetchone()
  except:
    socorro.lib.util.reportExceptionAndAbort(logger)
  
  start_time = row[0]
  end_time = start_time + p_interval
  now = now

if end_time > now:
  end_time = now

initLoop = True


while end_time <= now and initLoop:
  if end_time > now and end_time < (now + p_interval):
    end_time = now
  if configContext.initMode:
    logger.info("Init mode selected. Using big query!")
    sql = "SELECT %s FROM reports WHERE date>='%s'" % (",".join(columns), initModeDate)
  else:
    sql = "SELECT %s FROM reports WHERE date>='%s' AND date <='%s'" % (",".join(columns), start_time, end_time)
    logger.info("Beginning Data Slurp")
  
  try:
    cur.execute(sql)
    rows = cur.fetchall()
  except:
    socorro.lib.util.reportExceptionAndAbort(logger)

  logger.info("Queried %d rows with %s." % (len(rows), sql))

  ## This loop slurps up the data into our dictionary ##
  for row in rows:
    if row['product'] and row['version'] and row['signature']:
      key = (row['product'], row['version'], row['build'])
      fullKey = (row['product'], row['version'], row['build'], row['signature'])
      signature = row['signature']
      if key not in summary_crashes:
        summary_crashes[key] = {}
      else:
        if signature not in summary_crashes[key]:
          summary_crashes[key][signature] = {}
          summary_crashes[key][signature]['win'] = 0
          summary_crashes[key][signature]['lin'] = 0
          summary_crashes[key][signature]['mac'] = 0
          summary_crashes[key][signature]['uptime'] = 0
          summary_crashes[key][signature]['product'] = row['product']
          summary_crashes[key][signature]['version'] = row['version']
          summary_crashes[key][signature]['build'] = row['build']
          summary_crashes[key][signature]['signature'] = row['signature']
          summary_crashes[key][signature]['user_ids'] = [row['user_id']]
          summary_crashes[key][signature]['users'] = 1
          crash_count[fullKey] = 1.0
        else:
          crash_count[fullKey] += 1.0
          if not summary_crashes[key][signature]['user_ids'].count(row['user_id']):
            summary_crashes[key][signature]['user_ids'].append(row['user_id'])
            summary_crashes[key][signature]['users'] += 1
          
          if summary_crashes[key][signature]['uptime']:
            summary_crashes[key][signature]['uptime'] += row['uptime']
          else:
            summary_crashes[key][signature]['uptime'] = row['uptime']
        
          if row['os_name'] == "Mac OS X":
            summary_crashes[key][signature]['mac'] += 1

          if row['os_name'] == "Windows" or row['os_name'] == "Windows NT":
            summary_crashes[key][signature]['win'] += 1

          if row['os_name'] == "Linux":
            summary_crashes[key][signature]['lin'] += 1

  calc_tots(summary_crashes,crash_count)
  
  for pvCombo, data in summary_crashes.items():
      calc_ranks(summary_crashes[pvCombo])

  ### Do the DB updates ###
  update_time = end_time

  sql1 = "SELECT rank FROM topcrashers WHERE product=%s AND version=%s AND build=%s AND signature=%s ORDER BY last_updated DESC LIMIT 1" # Find the last rank of the current signature combo
  sql2 = "INSERT INTO topcrashers VALUES (DEFAULT, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)" # Insert new rows

  logger.info("Beginning DB update")
  for pvCombo, data in summary_crashes.items():
    for signature, signatureData in summary_crashes[pvCombo].items():
      try:
        cur.execute(sql1, (signatureData['product'], signatureData['version'], signatureData['build'], signatureData['signature']))
        row = cur.fetchall()
        if row:
          last_rank = row[0]['rank']
        else:
          last_rank = 0
        
        if configContext.debug:
          logger.debug("%s has the last_rank of %d." % ((pvCombo, signature), last_rank))

      except:
        socorro.lib.util.reportExceptionAndAbort(logger)
      
      try:
        cur.execute(sql2, (signatureData['signature'], signatureData['version'], signatureData['product'], signatureData['build'], signatureData['total'], signatureData['win'], signatureData['mac'], signatureData['lin'], signatureData['rank'], last_rank, "", signatureData['uptime_average'], signatureData['users'], update_time))
        conn.commit()
        
        if configContext.debug:
          logger.debug(sql2 % (signatureData['signature'], signatureData['version'], signatureData['product'], signatureData['build'], signatureData['total'], signatureData['win'], signatureData['mac'], signatureData['lin'], signatureData['rank'], last_rank, "", signatureData['uptime_average'], signatureData['users'], update_time))
     
      except:
        socorro.lib.util.reportExceptionAndAbort(logger)
    
    logger.info("DB Update complete.")
  start_time = end_time
  end_time += p_interval
  
  summary_crashes = {}
  crash_count = {}
  if configContext.initMode:
    initLoop = False
