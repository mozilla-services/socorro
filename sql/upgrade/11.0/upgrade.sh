#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=11.0

echo '*********************************************************'
echo 'functions for adding new releases manually and changing featured versions'
echo 'changes based on mware coding'
echo 'bug 752074'
psql -f ${CURDIR}/support_functions.sql breakpad
psql -f ${CURDIR}/add_release.sql breakpad
psql -f ${CURDIR}/feature_versions.sql breakpad

echo '*********************************************************'
echo 'add product sorting column to product_info'
echo 'bug ??????'
psql -f ${CURDIR}/product_views.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0