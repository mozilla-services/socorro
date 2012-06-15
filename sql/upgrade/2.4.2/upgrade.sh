#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=2.4.2

echo '*********************************************************'
echo 'support functions'
psql -f ${CURDIR}/support_functions.sql breakpad

echo '*********************************************************'
echo 'initialize cronjobs table for daily matviews'
echo 'bug 722395'
psql -f ${CURDIR}/initialize_daily_jobs_cronjobs.sql breakpad

echo '*********************************************************'
echo 'add archtecture and cores information to reports_clean'
echo 'may take quite a while for backfilling data'
echo 'bug 722934'
psql -f ${CURDIR}/add_arch_to_reports_clean.sql breakpad
psql -f ${CURDIR}/reports_clean_weekly.sql breakpad
psql -f ${CURDIR}/update_reports_clean.sql breakpad
${CURDIR}/backfill_arch_cores.py -s '2011-12-23' -m '1GB'

echo '*********************************************************'
echo 'create tables and functions for correlation reports'
echo 'and fill in some data.  will take a few minutes'
echo 'bug 722396'
psql -f ${CURDIR}/create_correlations_tables.sql breakpad
psql -f ${CURDIR}/update_correlations.sql breakpad
psql -f ${CURDIR}/backfill_matviews.sql breakpad
psql -f ${CURDIR}/fill_in_correlations.sql breakpad


#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0