#!/usr/bin/python

import psycopg2
import psycopg2.extensions
import psycopg2.extras
from optparse import OptionParser
import datetime
from datetime import datetime
from datetime import date
import os

parser = OptionParser()
parser.add_option("-D", "--database", dest="dbname",
                  help="database to upgrade", metavar="DBNAME",
                  default="breakpad")
parser.add_option("-p", "--port", dest="dbport",
                  help="database port", metavar="DBPORT",
                  default="5432")
parser.add_option("-h", "--host", dest="dbhost",
                  help="database hostname", metavar="DBHOST",
                  default="localhost")
parser.add_option("-l", "--log", dest="logfile",
                  help="logfile location for output",
                  metavar="LOGFILE", default="backfill.log")
parser.add_option("-s", "--start", dest="start",
                  help="UTC date to backfill from (required)", metavar="YYYY-MM-DD:HR")
parser.add_option("-e", "--end", dest="end",
                  help="UTC date to backfill to (inclusive)", metavar="YYYY-MM-DD:HR"
parser.add_option("-N", "--no_hourly", dest="no_hourly",
                  action="store_true", help="exclude hourly backfill")
parser.add_option("-A", "--adu", dest="adu",
                  action="store_true", help="backfill only matviews which use adu")
parser.add_option("-m", "--matviews", dest="matviews",
                  help="list of mativews to backfill", metavar="MV1,MV2,MV3")
parser.add_option("-c", "--classes", dest="classes",
				  help="list of matview classes to backfill", metavar="C1,C2")
(options, args) = parser.parse_args()
if not options.start:
	parser.error('No start date supplied')

# this script must run in UTC

os.environ['TZ'] = 'UTC'

# check, convert dates

startdate = datetime.strptime(options.start, "%Y-%m-%d:%H")
if options.enddate:
	enddate = datetime.strptime(options.end, "%Y-%m-%d:%H")
else:
	# if no enddate supplied, backfill to 3 hours ago
	enddate = datetime.today() - timedelta(hours=3)

# convert matview list, if supplied

if options.matviews:
	allmatviews = False
	runmatviews = options.matviews.split(',')
else:
	allmativews = True

# class list, if supplied

if options.classes:
	runclasses = options.classes.split(',')
else:
	runclasses = [ 'cumulative','hourly','daily','lastday' ]

# connect to database

conn = psycopg2.connect("dbname=%s user=postgres"
                        % ( options.dbname, ) )
cur = conn.cursor()

# run all jobs marked "cumulative"

def getjoblist ( jobclass, jobdate ):

	if jobclass in runclasses:
		getsql = """SELECT DISTINCT backfill_function
						FROM matview_control
						WHERE timing = '%s'
						  AND enabled """ % jobclass
		if not allmatviews then:
			getsql += " AND matview IN ( %s ) " % options.matviews
		if options.adu then:
			getsql += " AND adu_related "
		getsql += " ORDER BY fill_order;"
	else
		return false



run_jobs( cur, getsql )

# for each day in backfill period:

# a. run hourly jobs

# b. run daily jobs

# update successful day

# run "last day only" jobs for last successful day

# exit

startts = datetime.date.today() - datetime.timedelta(weeks=options.weeks)
enddate = datetime.date.today() - datetime.timedelta(days=1)

def funcdateloop( mycur, starts, ends, fillfunc ):
	curdate = starts
	while (curdate <= ends):
		qrytext = """SELECT %s('%s',false)""" % ( fillfunc, curdate.strftime("%Y-%m-%d"), )
		mycur.execute(qrytxt)
		curdate = curdate + datetime.timedelta(days=1)

conn = psycopg2.connect("dbname=%s user=postgres"
                        % ( options.dbname, ) )
cur = conn.cursor()

# populate build_adu back X weeks

print 'backfilling %d weeks of build_adu'
funcdateloop(cur, startdate, enddate, 'update_build_adu');

# copy over daily_crashes back to the beginning of product_adu
# up to the beginning of the backfill era
# to crash_by_user

print 'copying data from daily_crashes to crashes_by_user'

cur.execute("""INSERT INTO crashes_by_user (
	( product_version_id, os_short_name, crash_type_id,
		report_date, report_count, adu )
	SELECT productdims_id, os_short_name, crash_type_id,
		adu_day, count, adu_count
	FROM daily_crashes JOIN product_versions
		ON productdims_id = product_versions.product_version_id
		JOIN crash_types ON report_type = old_code
	    JOIN product_adu ON productdims_id = product_adu.product_version_id
	WHERE adu_day < %s """, ( startdate, ) )

# now backfill the rest
print 'backfilling %d weeks of crash_by_user'
funcdateloop(cur, startdate, enddate, 'update_crash_by_user');

# populate crash_by_user_build back X weeks

print 'backfilling %d weeks of crash_by_user_build'
funcdateloop(cur, startdate, enddate, 'update_crash_by_user_build');

# populate home_page_graph back X weeks
print 'backfilling %d weeks of home_page_graph'
funcdateloop(cur, startdate, enddate, 'update_home_page_graph');

# populate home_page_graph_build back X weeks
print 'backfilling %d weeks of home_page_graph_build'
funcdateloop(cur, startdate, enddate, 'update_home_page_graph_build');

# populate tcbs_build back X weeks
print 'backfilling %d weeks of tcbs_build'
funcdateloop(cur, startdate, enddate, 'update_tcbs_build');

print 'done backfilling'
print 'you may now run QA automation'
