#!/usr/bin/python
import sys, os
import psycopg2, psycopg2.extensions

# extracts a database from a copy of production breakpad
# consisting of only the last # weeks of data, more or less
# the resulting tgz file needs to be loaded with load_extractdb.py
# does not currently dump users

if len(sys.argv) > 1:
   num_weeks = sys.argv[1]
else:
   #extract two weeks if not given a parameter
   num_weeks = 2

# simple shell command runner
def rundump(dump_command):
   dump_result = os.system(dump_command)
   if dump_result != 0:
      sys.exit(dump_result)

print "Extracting %s weeks of data" % num_weeks

#connect to postgresql
conn = psycopg2.connect("dbname=breakpad user=postgres")

cur = conn.cursor()

# get the list of partitions NOT to dump
cur.execute("""
SELECT array_to_string( array_agg ( ' -T ' || relname ), ' ' )
         FROM pg_stat_user_tables
         WHERE relname ~* $x$_20\d+$$x$
AND substring(relname FROM $x$_(20\d+)$$x$) <
 to_char( ( now() - ( %s * interval '1 week') ), 'YYYYMMDD');
   """, ( num_weeks, ) )

no_dump = str(cur.fetchone()[0]) + ' -T performance_check_1 -T raw_adu -T top_crashes_by_signature -T top_crashes_by_url -T top_crashes_by_url_signature -T top_crashes_by_url_id_seq -T top_crashes_by_signature_id_seq'
# don't dump the matviews either

#get the date of truncation
cur.execute ("""
             SELECT to_date(substring(relname FROM $x$_(20\d+)$$x$),'YYYYMMDD')
               FROM pg_stat_user_tables
            WHERE relname LIKE 'reports_20%%'
         AND substring(relname FROM $x$_(20\d+)$$x$) >=
to_char( ( now() - ( %s * interval '1 week') ), 'YYYYMMDD')
            ORDER BY relname LIMIT 1;
             """, ( num_weeks, ) )

cutoff_date = str(cur.fetchone()[0])

print "truncating all data before %s" % cutoff_date

#pg_dump most of the database
print 'dumping most of the database'
rundump('pg_dump -Fc -U postgres ' + no_dump + ' breakpad -f extractdb.dump' )

#pg_dump the schema for the matview tables
print 'dumping matviews'
rundump('pg_dump -Fc -U postgres -s -t raw_adu -t top_crashes_by_signature -t top_crashes_by_url -t top_crashes_by_url_signature breakpad -f matviews.dump' )

#COPY the truncated data for raw_adu
dumpadu = """psql -U postgres -c "\copy ( SELECT * FROM raw_adu WHERE raw_adu.date >= '%s' ) to raw_adu.dump" breakpad""" % cutoff_date
rundump(dumpadu);

#COPY the truncated data for top_crashes_by_signature
dumptcbs = """psql -U postgres -c "\copy ( SELECT * FROM top_crashes_by_signature WHERE window_end >= '%s' ) to tcbs.dump" breakpad""" % cutoff_date
rundump(dumptcbs);

#COPY the truncated data for tcbu
dumptcbu = """psql -U postgres -c "\copy ( SELECT * FROM top_crashes_by_url WHERE window_end >= '%s' ) to tcbu.dump" breakpad""" % cutoff_date
rundump(dumptcbu);

#COPY the truncated data for tcbu_s
dumptcbus = """psql -U postgres -c "\copy ( SELECT tcbu_s.* FROM top_crashes_by_url_signature tcbu_s JOIN top_crashes_by_url ON top_crashes_by_url_id = top_crashes_by_url.id WHERE window_end >= '%s' ) to tcbu_s.dump" breakpad""" % cutoff_date
rundump(dumptcbus);

#DUMP the users and logins

rundump('pg_dumpall -U postgres -g -f users.dump')

rundump('tar -cvzf extractdb.tgz extractdb.dump matviews.dump raw_adu.dump tcbs.dump tcbu.dump tcbu_s.dump users.dump')
rundump('rm extractdb.dump matviews.dump raw_adu.dump tcbs.dump tcbu.dump tcbu_s.dump users.dump')

print 'done extracting database'
