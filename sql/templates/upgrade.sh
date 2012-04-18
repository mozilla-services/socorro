#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
VERSION=#.#

#echo '*********************************************************'
#echo 'support functions'
#psql -f ${CURDIR}/support_functions.sql breakpad

echo '*********************************************************'
echo 'fix '
echo 'no bug'
psql -f ${CURDIR}/_____.sql breakpad

echo '*********************************************************'
echo 'fix '
echo 'bug ######'
psql -f ${CURDIR}/_____.sql breakpad
psql -f ${CURDIR}/_____.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0