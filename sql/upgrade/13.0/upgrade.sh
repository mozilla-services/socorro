#!/bin/bash
#please see README

set -e

CURDIR=$(dirname $0)
DBNAME=$1
: ${DBNAME:="breakpad"}
VERSION=13.0

echo '*********************************************************'
echo 'replace processor monitoring view for ganglia'
echo 'bug 764468'
psql -f ${CURDIR}/processor_monitoring.sql $DBNAME

echo '*********************************************************'
echo 'modify add_new_release to better support ftpscraper'
echo 'bug 763552'
psql -f ${CURDIR}/add_release.sql $DBNAME

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" $DBNAME

echo "$VERSION upgrade done"

exit 0