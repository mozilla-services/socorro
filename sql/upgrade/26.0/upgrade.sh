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

psql -f ${CURDIR}/backfill_one_day_319793.sql $DBNAME
psql -f ${CURDIR}/backfill_one_day_319794.sql $DBNAME
psql -f ${CURDIR}/backfill_daily_crashes.sql $DBNAME
psql -f ${CURDIR}/backfill_reports_duplicates.sql $DBNAME
psql -f ${CURDIR}/update_adu.sql $DBNAME
psql -f ${CURDIR}/update_build_adu.sql $DBNAME
psql -f ${CURDIR}/update_correlations.sql $DBNAME
psql -f ${CURDIR}/update_crashes_by_user.sql $DBNAME
psql -f ${CURDIR}/update_crashes_by_user_build.sql $DBNAME
psql -f ${CURDIR}/update_daily_crashes.sql $DBNAME
psql -f ${CURDIR}/update_explosiveness.sql $DBNAME
psql -f ${CURDIR}/update_home_page_graph.sql $DBNAME
psql -f ${CURDIR}/update_home_page_graph_build.sql $DBNAME
psql -f ${CURDIR}/update_nightly_builds.sql $DBNAME
psql -f ${CURDIR}/update_os_versions.sql $DBNAME
psql -f ${CURDIR}/update_os_versions_new_reports.sql $DBNAME
psql -f ${CURDIR}/update_rank_compare.sql $DBNAME
psql -f ${CURDIR}/update_reports_clean.sql $DBNAME
psql -f ${CURDIR}/update_reports_duplicates.sql $DBNAME
psql -f ${CURDIR}/update_signatures.sql $DBNAME
psql -f ${CURDIR}/update_tcbs.sql $DBNAME
psql -f ${CURDIR}/update_tcbs_build.sql $DBNAME

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" $DBNAME

echo "$VERSION upgrade done"

exit 0
