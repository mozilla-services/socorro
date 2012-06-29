#!/usr/bin/python

import psycopg2
import psycopg2.extensions
import psycopg2.extras
from optparse import OptionParser
import datetime

parser = OptionParser()
parser.add_option("-D", "--database", dest="dbname",
                  help="database to upgrade", metavar="DBNAME",
                  default="breakpad")
parser.add_option("-w", "--weeks", dest="weeks",
                  help="weeks to backfill", metavar="WEEKS",
                  default="2")
(options, args) = parser.parse_args()

# calculate weeks

startdate = datetime.date.today() - datetime.timedelta(weeks=options.weeks)
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

# drop daily_crashes, since we don't need it anymore
cur.execute("""DROP TABLE IF EXISTS daily_crashes""")

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
