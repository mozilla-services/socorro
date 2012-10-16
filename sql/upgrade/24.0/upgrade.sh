#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

#please see README

set -e

CURDIR=$(dirname $0)
DBNAME=$1
: ${DBNAME:="breakpad"}
VERSION=24.0

echo '*********************************************************'
echo 'fix permissions for user analyst on new matviews'
echo 'no bug'
psql -f ${CURDIR}/analyst_grants.sql $DBNAME

echo '*********************************************************'
echo 'provide data source for stability report for direct'
echo 'access by analytics users.'
echo 'bug 768059'
psql -f ${CURDIR}/update_adu.sql $DBNAME
psql -f ${CURDIR}/update_crashes_by_user.sql $DBNAME
psql -f ${CURDIR}/stability_report.sql $DBNAME

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" $DBNAME

echo "$VERSION upgrade done"

exit 0