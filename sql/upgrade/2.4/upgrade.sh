#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=2.4

echo "begin $VERSION database upgrade"
echo '*********************************************'
echo 'switch tcbs and daily_crashes to using reports_clean'
echo 'bug 701255'
psql -f ${CURDIR}/update_tcbs.sql breakpad
psql -f ${CURDIR}/daily_crashes.sql breakpad
psql -f ${CURDIR}/backfill_matviews.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0