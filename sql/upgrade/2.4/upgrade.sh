#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)

echo 'switch tcbs and daily_crashes to using reports_clean'
echo 'bug 701255'
psql -f ${CURDIR}/update_tcbs.sql breakpad
psql -f ${CURDIR}/daily_crashes.sql breakpad
psql -f ${CURDIR}/backfill_matviews.sql breakpad

echo 'create new signature summaries index and function'
echo 'may take quite a while for index creation
echo 'bug 714338'
psql -f ${CURDIR}/new_rc_index.sql breakpad
psql -f ${CURDIR}/reports_clean_weekly.sql breakpad
psql -f ${CURDIR}/signature_summary_function.sql breakpad



echo '2.4 upgrade done'

exit 0