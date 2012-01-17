#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=2.4

echo '*********************************************************'
echo 'support functions'
psql -f ${CURDIR}/create_table_if_not_exists.sql breakpad

echo '*********************************************************'
echo 'create new signature summaries index and function'
echo 'may take quite a while for index creation'
echo 'bug 714338 and '
psql -f ${CURDIR}/new_rc_index.sql breakpad
psql -f ${CURDIR}/reports_clean_weekly.sql breakpad

# not needed, doing in middelware instead
# psql -f ${CURDIR}/signature_summary_function.sql breakpad

echo '*********************************************************'
echo 'create rank compare matview and backfill'
echo 'should take around 3 minutes'
echo 'bug 640237'
psql -f ${CURDIR}/rank_compare.sql breakpad
psql -f ${CURDIR}/populate_rank_compare.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0