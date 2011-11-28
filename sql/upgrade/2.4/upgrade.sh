#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)

echo 'switch tcbs and daily_crashes to using reports_clean'
echo 'bug 701255'
psql -f ${CURDIR}/update_tcbs.sql breakpad
psql -f ${CURDIR}/daily_crashes.sql breakpad
psql -f ${CURDIR}/backfill_matviews.sql breakpad

echo '2.4 upgrade done'

exit 0