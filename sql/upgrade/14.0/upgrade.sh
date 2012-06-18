#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
DBNAME=$1
: ${DBNAME:="breakpad"}
VERSION=14.0

#echo '*********************************************************'
#echo 'support functions'
#psql -f ${CURDIR}/support_functions.sql $DBNAME

echo '*********************************************************'
echo 'add WebRuntime to list of products'
echo 'bug 759724'
psql -f ${CURDIR}/add_webrt.sql $DBNAME
psql -f ${CURDIR}/update_products.sql $DBNAME

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" $DBNAME

echo "$VERSION upgrade done"

exit 0