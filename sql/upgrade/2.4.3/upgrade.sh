#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=2.4.3

#echo '*********************************************************'
#echo 'support functions'
#psql -f ${CURDIR}/support_functions.sql breakpad

echo '*********************************************************'
echo 'fix sorting for 3-digit betas'
echo 'bug 721456'
psql -f ${CURDIR}/new_version_sort.sql breakpad
psql -f ${CURDIR}/backfill_version_sorts.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0