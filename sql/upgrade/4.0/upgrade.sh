#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=4.0

#echo '*********************************************************'
#echo 'support functions'
#psql -f ${CURDIR}/support_functions.sql breakpad

echo '*********************************************************'
echo 'add startup crash count to TCBS'
echo 'bug 738323'
psql -f ${CURDIR}/add_startup_crashes_col.sql breakpad
psql -f ${CURDIR}/update_tcbs.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0