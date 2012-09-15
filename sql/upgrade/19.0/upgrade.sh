#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

#please see README

set -e

CURDIR=$(dirname $0)
DBNAME=$1
: ${DBNAME:="breakpad"}
VERSION=19.0

#echo '*********************************************************'
#echo 'support functions'
#psql -f ${CURDIR}/support_functions.sql $DBNAME

echo '*********************************************************'
echo 'fix product_crash_ratio view for analytics'
echo 'bug 790844'
psql -f ${CURDIR}/product_crash_ratio.sql $DBNAME

echo '*********************************************************'
echo 'fix performance_check_1 for ganglia'
echo 'no bug'
psql -f ${CURDIR}/performance_check_1.sql $DBNAME

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" $DBNAME

echo "$VERSION upgrade done"

exit 0