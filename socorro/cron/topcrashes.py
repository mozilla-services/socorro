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

import psycopg2
import psycopg2.extras

import topcrashes_config as config
import socorro.lib.ConfigurationManager as configurationManager

import socorro.lib.util

def calc_tots(crashes, crash_count):
  """ Calculate the total number of crashes per signature combo, as well as uptime averages. """
  for signature, data in crashes.items():
    crashes[signature]['total'] = data['win'] + data['mac'] + data['lin']
    crashes[signature]['uptime_average'] = crashes[signature]['uptime'] / crash_count[signature]
  if configContext.debug:
    for signature, data in crashes.items():
      logger.debug("%s Total: %d" % (signature, crashes[signature]['total']))
      logger.debug("%s Uptime Average: %d" % (signature, crashes[signature]['uptime_average']))
    
def calc_ranks(crashes):
  """ Calculate the new ranks of the crashes, by total number of crashes """
  ranks = []
  
  for signature, data in crashes.items():
    ranks.append([signature, data['total']])
  
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
  logger.info("Wasn't able to start due to configuration options.")
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


columns = ["product", "version", "signature", "uptime", "os_name", "user_id"]

if configContext.initMode:
  logger.info("Init mode selected. Using big query!")
  sql = "SELECT %s FROM reports" % (",".join(columns))
else:
  sql = "SELECT %s FROM reports WHERE date>=(SELECT last_updated FROM topcrashers ORDER BY last_updated DESC LIMIT 1)" % (",".join(columns))

logger.info("Beginning Data Slurp")
try:
  cur.execute(sql)
  rows = cur.fetchall()
except:
  socorro.lib.util.reportExceptionAndAbort(logger)

logger.info("Queried %d rows with %s." % (len(rows), sql))

## This loop slurps up the data into our dictionary ##
for row in rows:
  key = (row['product'], row['version'], row['signature'])
  if key not in summary_crashes:
    summary_crashes[key] = {}
    summary_crashes[key]['win'] = 0
    summary_crashes[key]['lin'] = 0
    summary_crashes[key]['mac'] = 0
    summary_crashes[key]['uptime'] = 0
    summary_crashes[key]['product'] = row['product']
    summary_crashes[key]['version'] = row['version']
    summary_crashes[key]['signature'] = row['signature']
    summary_crashes[key]['user_ids'] = [row['user_id']]
    summary_crashes[key]['users'] = 1
    crash_count[key] = 1.0
  else:
    crash_count[key] += 1.0
    if not summary_crashes[key]['user_ids'].count(row['user_id']):
      summary_crashes[key]['user_ids'].append(row['user_id'])
      summary_crashes[key]['users'] += 1
      
  if summary_crashes[key]['uptime']:
    summary_crashes[key]['uptime'] += row['uptime']
  else:
    summary_crashes[key]['uptime'] = row['uptime']
  
  if row['os_name'] == "Mac OS X":
    summary_crashes[key]['mac'] += 1

  if row['os_name'] == "Windows" or row['os_name'] == "Windows NT":
    summary_crashes[key]['win'] += 1

  if row['os_name'] == "Linux":
    summary_crashes[key]['lin'] += 1

calc_tots(summary_crashes,crash_count)
calc_ranks(summary_crashes)

### Do the DB updates ###

sql1 = "SELECT rank FROM topcrashers WHERE product=%s AND version=%s AND signature=%s ORDER BY last_updated DESC LIMIT 1" # Find the last rank of the current signature combo
sql2 = "INSERT INTO topcrashers VALUES (DEFAULT, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())" # Insert new rows

logger.info("Beginning DB update")
for signature, data in summary_crashes.items():
  try:
    cur.execute(sql1, (data['product'], data['version'], data['signature']))
    row = cur.fetchall()
    if row:
      last_rank = row[0]['rank']
    else:
      last_rank = 0
    
    if configContext.debug:
      logger.debug("%s has the last_rank of %d." % (signature, last_rank))

  except:
    socorro.lib.util.reportExceptionAndAbort(logger)
  
  try:
    cur.execute(sql2, (data['signature'], data['version'], data['product'], data['total'], data['win'], data['mac'], data['lin'], data['rank'], last_rank, "", data['uptime_average'], data['users']))
    conn.commit()
    
    if configContext.debug:
      logger.debug(sql2 % (data['signature'], data['version'], data['product'], data['total'], data['win'], data['mac'], data['lin'], data['rank'], last_rank, "", data['uptime_average'], data['users']))
 
  except:
    socorro.lib.util.reportExceptionAndAbort(logger)
logger.info("DB Update complete.")
