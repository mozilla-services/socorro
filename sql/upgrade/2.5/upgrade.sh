#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

#please see README

set -e

CURDIR=$(dirname $0)
VERSION=2.5.0

echo '*********************************************************'
echo 'support functions'
psql -f ${CURDIR}/support_functions.sql breakpad

echo '*********************************************************'
echo 'modify existing ESR crash data to conform with new spec'
echo 'will take up to 20 minutes'
echo 'bug 729195'
psql -f ${CURDIR}/fix_esr_data.sql breakpad

echo '*********************************************************'
echo 'fix version sorts for ESR releases'
echo 'bug 729195'
psql -f ${CURDIR}/new_version_sort.sql breakpad
psql -f ${CURDIR}/backfill_version_sorts.sql breakpad

echo '*********************************************************'
echo 'fix matview functions to support ESR releases'
echo 'bug 729195'
psql -f ${CURDIR}/update_adu.sql breakpad
psql -f ${CURDIR}/update_products.sql breakpad
psql -f ${CURDIR}/update_reports_clean.sql breakpad

echo '*********************************************************'
echo 'add table for rule-based transforms to database'
echo 'bug 731000'
psql -f ${CURDIR}/transform_rules.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0