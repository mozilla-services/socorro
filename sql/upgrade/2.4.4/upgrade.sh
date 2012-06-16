#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

#please see README

set -e

CURDIR=$(dirname $0)
VERSION=2.4.4

#echo '*********************************************************'
#echo 'support functions'
#psql -f ${CURDIR}/support_functions.sql breakpad

echo '*********************************************************'
echo 'add matview to support nightly builds chart'
echo 'bug 640238'
psql -f ${CURDIR}/nightly_builds.sql breakpad
psql -f ${CURDIR}/backfill_matviews.sql breakpad

echo '*********************************************************'
echo 'drop frames table'
echo 'bug 681476'
psql -f ${CURDIR}/drop_frames_table.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0