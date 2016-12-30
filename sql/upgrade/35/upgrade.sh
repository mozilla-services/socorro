#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

#please see README

set -e

CURDIR=$(dirname $0)
DBNAME=$1
: ${DBNAME:="breakpad"}
VERSION=34.0

echo '*********************************************************'
echo 'Add emails table'
echo 'bug 814647'
psql -f ${CURDIR}/emails.sql $DBNAME

echo "$VERSION upgrade done"

exit 0
