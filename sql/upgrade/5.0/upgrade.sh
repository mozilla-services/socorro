#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=5.0

#echo '*********************************************************'
#echo 'support functions'
#psql -f ${CURDIR}/support_functions.sql breakpad

echo '*********************************************************'
echo 'data source for explosiveness'
echo 'bug 733021'
psql -f ${CURDIR}/explosive_crashes.sql breakpad

echo '*********************************************************'
echo 'make crash ratio views match UI'
echo 'bug 738394'
psql -f ${CURDIR}/product_crash_ratio.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0