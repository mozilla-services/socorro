#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=2.3.5

echo "begin $VERSION database upgrade"

echo '*********************************************'
echo 'various support functions'
echo 'no bug'
psql -f ${CURDIR}/create_column_if_not_exists.sql breakpad
psql -f ${CURDIR}/update_socorro_version.sql breakpad
psql -f ${CURDIR}/create_table_if_not_exists.sql breakpad

echo '*********************************************'
echo 'add productid column to reports'
echo 'may require time for locking'
echo 'bug 706807'
psql -f ${CURDIR}/productid.sql breakpad

echo '*********************************************'
echo 'add FennecAndroid to products list'
echo 'bug 706893'
psql -f ${CURDIR}/add_fennec_android.sql breakpad

echo '*********************************************'
echo 'add support for fennecandroid to ADU'
echo 'bug 710866'
psql -f ${CURDIR}/adu_product_guid.sql breakpad
psql -f ${CURDIR}/update_adu.sql breakpad

echo '*********************************************'
echo 'create productid mapping table'
echo 'bug 706900'
psql -f ${CURDIR}/productid_mapping_table.sql breakpad

echo '*********************************************'
echo 'modify update_products to pull FennecAndroid'
echo 'bug 706899'
psql -f ${CURDIR}/productid_mapping_table.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0