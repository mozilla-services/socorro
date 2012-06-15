#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=8.0

echo '*********************************************************'
echo 'fix math for explosive crashes '
echo 'bug 744492'
psql -f ${CURDIR}/explosive_crashes.sql breakpad

# bumped to 9.0 due to test failure
#echo '*********************************************************'
#echo 'restrict product_version_builds to main repositories'
#echo 'bug 748194'
#psql -f ${CURDIR}/update_products_repos.sql breakpad

echo '*********************************************************'
echo 'fix crash_ratio'
echo 'bug 749842'
psql -f ${CURDIR}/product_crash_ratio.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0