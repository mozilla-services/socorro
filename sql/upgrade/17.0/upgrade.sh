#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

set -e

CURDIR=$(dirname $0)
VERSION=15.
DBNAME=$1
: {DBNAME:="breakpad"}

echo '*********************************************************'
echo 'support functions'
psql -f ${CURDIR}/support_functions.sql $DBNAME

echo '*********************************************************'
echo 'copy old products to new tables'
psql -f ${CURDIR}/copy_old_products_to_product_versions.sql $DBNAME

echo '*********************************************************'
echo 'add rapid_beta_version columns etc.'
psql -f ${CURDIR}/rapid_beta_version.sql $DBNAME

echo '*********************************************************'
echo 'purge oldtcbs tables'
psql -f ${CURDIR}/drop_oldtcbs.sql $DBNAME
psql -f ${CURDIR}/product_views.sql $DBNAME

echo '*********************************************************'
echo 'add rapid beta versions of functions'
psql -f ${CURDIR}/backfill_tcbs.sql $DBNAME
psql -f ${CURDIR}/backfill_tcbs_build.sql $DBNAME
psql -f ${CURDIR}/build_adu.sql $DBNAME
psql -f ${CURDIR}/crash_by_user.sql $DBNAME
psql -f ${CURDIR}/crash_by_user_build.sql $DBNAME
psql -f ${CURDIR}/home_page_graph.sql $DBNAME
psql -f ${CURDIR}/home_page_graph_build.sql $DBNAME
psql -f ${CURDIR}/product_crash_ratio.sql $DBNAME
psql -f ${CURDIR}/product_views.sql $DBNAME
psql -f ${CURDIR}/update_adu.sql $DBNAME
psql -f ${CURDIR}/update_products.sql $DBNAME
psql -f ${CURDIR}/update_reports_clean.sql $DBNAME
psql -f ${CURDIR}/update_tcbs_build.sql $DBNAME
psql -f ${CURDIR}/update_tcbs.sql $DBNAME



#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" $DBNAME

echo "$VERSION upgrade done"

exit 0