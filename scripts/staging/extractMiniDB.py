#!/usr/bin/python

import sys
import os
import psycopg2
import psycopg2.extensions
from optparse import OptionParser

# extracts a database from a copy of production breakpad
# consisting of only the last # weeks of data, more or less
# the resulting tgz file needs to be loaded with loadMiniDBonDev.py
# does not currently dump users

parser = OptionParser()
parser.add_option("-w", "--weeks", dest="num_weeks", type="int",
                  help="number of weeks to extract", metavar="#",
                  default=2)
parser.add_option("-d", "--database", dest="database_name",
                  help="database to be extracted", metavar="DBNAME",
                  default="breakpad")
parser.add_option("-f", "--file", dest="tar_file",
                  help="extractdb tarball to be created", metavar="FILE",
                  default="extractdb.tgz")

(options, args) = parser.parse_args()

# simple shell command runner
def rundump(dump_command):
    dump_result = os.system(dump_command)
    if dump_result != 0:
        sys.exit(dump_result)

print "Extracting %s weeks of data" % options.num_weeks

#connect to postgresql
conn = psycopg2.connect("dbname=%s user=postgres" % options.database_name)

cur = conn.cursor()

# get the list of weekly partitions to NOT dump
cur.execute("""
SELECT array_to_string( array_agg ( ' -T ' || relname ), ' ' )
        FROM pg_stat_user_tables
        WHERE relname ~* $x$_20\d+$$x$
AND substring(relname FROM $x$_(20\d+)$$x$) <
 to_char( ( now() - ( ( %s + 1 ) * interval '1 week') ), 'YYYYMMDD');
   """, (options.num_weeks,))

no_dump = str(cur.fetchone()[0])

#get the date of truncation
cur.execute("""
             SELECT to_date(substring(relname FROM $x$_(20\d+)$$x$),'YYYYMMDD')
               FROM pg_stat_user_tables
            WHERE relname LIKE 'reports_20%%'
         AND substring(relname FROM $x$_(20\d+)$$x$) >=
to_char( ( now() - ( ( %s + 1 ) * interval '1 week') ), 'YYYYMMDD')
            ORDER BY relname LIMIT 1;
             """, (options.num_weeks,))

cutoff_date = str(cur.fetchone()[0])

# dump the list of matviews one at a time.  consult dictionary
# for the queries to retrieve each set of truncated data

# cycle through the list of matviews
# and tables with data that needs to be cleaned
# dump those with no data

matviews = {'raw_adu'
    : """SELECT * FROM raw_adu WHERE raw_adu.date >= '%s'""" % cutoff_date,
    'top_crashes_by_signature'
    : """SELECT * FROM top_crashes_by_signature WHERE window_end >= '%s'""" % cutoff_date,
    'top_crashes_by_url'
    : """SELECT * FROM top_crashes_by_url WHERE window_end >= '%s'""" % cutoff_date,
    'top_crashes_by_url_signature'
    : """SELECT tcbus.* FROM top_crashes_by_url_signature tcbus JOIN top_crashes_by_url
        ON top_crashes_by_url_id = top_crashes_by_url.id
        WHERE top_crashes_by_url.window_end >= '%s'""" % cutoff_date,
    'releases_raw'
    : """SELECT releases_raw.* FROM releases_raw WHERE build_date(build_id)
        >= ( DATE '%s' - 180 ) """ % cutoff_date,
    'product_adu' : """SELECT product_adu.* FROM product_adu WHERE adu_date >= '%s'""" % cutoff_date,
   'daily_crashes'
    : """SELECT daily_crashes.* FROM daily_crashes WHERE adu_day >= '%s'""" % cutoff_date,
    'tcbs'
    : """SELECT tcbs.* FROM tcbs WHERE report_date >= '%s'"""
        % cutoff_date,
    'sessions' : """SELECT * FROM sessions WHERE false""",
    'server_status' : """SELECT * FROM server_status WHERE false""",
    'reports_bad' : """SELECT * FROM reports_bad WHERE false""",
    'reports_duplicates'
    : """SELECT * FROM reports_duplicates WHERE date_processed >= '%s'""" % cutoff_date,
    'daily_hangs'
    : """SELECT * FROM daily_hangs WHERE report_date >= '%s'""" % cutoff_date}

no_dump_all = no_dump + ' -T "priority_jobs_*" -T ' + ' -T '.join(matviews)
# don't dump priority jobs queues either

print "truncating all data before %s" % cutoff_date

#pg_dump most of the database
print 'dumping most of the database'
rundump('pg_dump -Fc -U postgres ' + no_dump_all + ' breakpad -f minidb.dump')

# copy truncated data for each matview

for matview in matviews:
        print 'dumping %s' % matview
        dumpstring = """psql -U postgres -c "\copy ( """ + matviews[matview] + """ ) to """ + matview + """.dump" breakpad"""
        rundump(dumpstring)

# dump the schema for the matviews:
rundump('pg_dump -Fc -s -t' + ' -t '.join(matviews) + ' -f matview_schemas.dump breakpad')

#DUMP the users and logins

rundump('pg_dumpall -U postgres -r -f users.dump')

#remove password sets

rundump('sed -i "s/PASSWORD \'.*\'//" users.dump')

rundump("tar -cvzf %s *.dump" % options.tar_file)
rundump('rm *.dump')

print 'done extracting database'
