#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=2.4

echo '*********************************************'
echo 'support functions'
psql -f ${CURDIR}/support_functions.sql breakpad

echo '*********************************************'
echo 'switch tcbs and daily_crashes to using reports_clean'
echo 'bugs 701255, 715335'
psql -f ${CURDIR}/update_tcbs.sql breakpad
psql -f ${CURDIR}/daily_crashes.sql breakpad
psql -f ${CURDIR}/backfill_matviews.sql breakpad

echo '*********************************************'
echo 'change all columns to timestamptz'
echo 'bug 715333'
psql -f ${CURDIR}/change_column_types.sql breakpad

echo '*********************************************'
echo 'rebuild constraints.  this may take up to 2 hours,'
echo 'and will produce LOTS of output while its working'
echo 'bug 715333'
/data/socorro/application/scripts/parallel_sql_jobs.py --dbname breakpad -j 8 --stop < /tmp/partition_constraints.txt

echo '*********************************************'
echo 'change data type on raw_adu and analyze the database'
echo 'this can take up to 40 min'
echo 'bug 715333'
psql -f ${CURDIR}/fix_adu_date.sql breakpad

echo '*********************************************'
echo 'fix matview generators to work with UTC'
echo 'bugs 715335'
psql -f ${CURDIR}/update_os_versions.sql breakpad
psql -f ${CURDIR}/update_reports_duplicates.sql breakpad
psql -f ${CURDIR}/update_reports_clean.sql breakpad
psql -f ${CURDIR}/update_signatures.sql breakpad
psql -f ${CURDIR}/insert_into_lookup_lists.sql breakpad

echo '*********************************************'
echo 'drop and fix timezone conversion functions'
echo 'bugs 715342'
psql -f ${CURDIR}/drop_tz_conversion_functions.sql breakpad

echo '*********************************************'
echo 'drop temporary tables created for conversion'
psql -f ${CURDIR}/drop_transitional_tables.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0