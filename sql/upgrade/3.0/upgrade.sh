#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=3.0

#echo '*********************************************************'
#echo 'support functions'
#psql -f ${CURDIR}/support_functions.sql breakpad

echo '*********************************************************'
echo 'add middleware function for retrieving lists of product-versions'
echo 'no bug'
psql -f ${CURDIR}/get_product_version_ids.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0