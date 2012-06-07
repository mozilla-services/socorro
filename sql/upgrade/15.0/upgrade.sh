#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=15.0
DBNAME=$1
: {DBNAME:="breakpad"}

echo '*********************************************************'
echo 'support functions'
psql -f ${CURDIR}/support_functions.sql $DBNAME

echo '*********************************************************'
echo 'copy old products to new tables'
psql -f ${CURDIR}/copy_old_products_to_product_versions.sql $DBNAME

echo '*********************************************************'
echo 'purge oldtcbs tables'
psql -f ${CURDIR}/drop_oldtcbs.sql $DBNAME
psql -f ${CURDIR}/product_views.sql $DBNAME

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" $DBNAME

echo "$VERSION upgrade done"

exit 0