#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

#please see README

set -e

CURDIR=$(dirname $0)
DBNAME=$1
: ${DBNAME:="breakpad"}
VERSION=26.0

echo '*********************************************************'
echo 'Remove all memory parameters from functions'
echo 'bug 796153'


#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" $DBNAME

echo "$VERSION upgrade done"

exit 0
