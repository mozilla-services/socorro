#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=9.0

echo '*********************************************************'
echo 'restrict product_version_builds to main repositories'
echo 'bug 748194'
psql -f ${CURDIR}/update_products_repos.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0