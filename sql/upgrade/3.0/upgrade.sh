#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

#please see README

set -e

CURDIR=$(dirname $0)
VERSION=3.0

#echo '*********************************************************'
#echo 'support functions'
#psql -f ${CURDIR}/support_functions.sql breakpad

echo '*********************************************************'
echo 'add middleware function for retrieving lists of product-versions'
echo 'no bug'
psql -f ${CURDIR}/get_product_version_ids.sql breakpad

echo '*********************************************************'
echo 'drop build_date column from reports'
echo 'bug #729208'
psql -f ${CURDIR}/drop_reports_build_date.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0