#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=7.0

echo '*********************************************************'
echo 'fix '
echo 'bug ######'
psql -f ${CURDIR}/explosive_crashes.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0