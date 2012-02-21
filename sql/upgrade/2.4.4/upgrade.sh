#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=2.4.4

#echo '*********************************************************'
#echo 'support functions'
#psql -f ${CURDIR}/support_functions.sql breakpad

echo '*********************************************************'
echo 'add matview to support nightly builds chart'
echo 'bug 640238'
psql -f ${CURDIR}/nightly_builds.sql breakpad
psql -f ${CURDIR}/backfill_matviews.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0