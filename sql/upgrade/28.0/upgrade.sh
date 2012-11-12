#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

#please see README

set -e

CURDIR=$(dirname $0)
DBNAME=$1
: ${DBNAME:="breakpad"}
VERSION=28.0

echo '*********************************************************'
echo 'Add exploitability column to reports'
echo 'bug 807349'
psql -f ${CURDIR}/exploitability_column.sql $DBNAME
echo 'Add FlashProcessDump to reports and reports_clean'
echo 'bug 773332'
psql -f ${CURDIR}/add_flash_process_dump.sql $DBNAME

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" $DBNAME

echo "$VERSION upgrade done"

exit 0
