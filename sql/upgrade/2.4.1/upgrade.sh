#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)

echo 'create new signature summaries index and function'
echo 'may take quite a while for index creation
echo 'bug 714338'
psql -f ${CURDIR}/new_rc_index.sql breakpad
psql -f ${CURDIR}/reports_clean_weekly.sql breakpad
psql -f ${CURDIR}/signature_summary_function.sql breakpad

echo '2.4.1 upgrade done'

exit 0