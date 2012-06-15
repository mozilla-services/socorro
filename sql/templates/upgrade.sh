#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
DBNAME=$1
: ${DBNAME:="breakpad"}
VERSION=#.#

#echo '*********************************************************'
#echo 'support functions'
#psql -f ${CURDIR}/support_functions.sql $DBNAME

echo '*********************************************************'
echo 'fix '
echo 'no bug'
psql -f ${CURDIR}/_____.sql $DBNAME

echo '*********************************************************'
echo 'fix '
echo 'bug ######'
psql -f ${CURDIR}/_____.sql $DBNAME
psql -f ${CURDIR}/_____.sql $DBNAME

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" $DBNAME

echo "$VERSION upgrade done"

exit 0