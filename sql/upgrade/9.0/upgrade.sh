#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=9.0

echo '*********************************************************'
echo 'support functions'
psql -f ${CURDIR}/support_functions.sql breakpad

echo '*********************************************************'
echo 'restrict product_version_builds to main repositories'
echo 'bug 748194'
psql -f ${CURDIR}/update_products_repos.sql breakpad

echo '*********************************************************'
echo 'functions for adding new releases manually and changing featured versions'
echo 'bug 752074'
psql -f ${CURDIR}/add_release.sql breakpad
psql -f ${CURDIR}/feature_versions.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0