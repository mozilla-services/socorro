#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

#please see README

set -e

CURDIR=$(dirname $0)
DBNAME=$1
: ${DBNAME:="breakpad"}
VERSION=21.0

echo '*********************************************************'
echo 'Add Android to known OS names, grouped in Linux'
echo 'bug 737267'
psql -f ${CURDIR}/update_correlations.sql $DBNAME
psql -f ${CURDIR}/update_daily_crashes.sql $DBNAME
psql -f ${CURDIR}/update_explosiveness.sql $DBNAME
psql -f ${CURDIR}/update_hang_report.sql $DBNAME
psql -f ${CURDIR}/update_nightly_builds.sql $DBNAME
psql -f ${CURDIR}/update_rank_compare.sql $DBNAME

echo "$VERSION upgrade done"

exit 0
