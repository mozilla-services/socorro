#!/bin/bash
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
echo 'backfill matviews for ESR data to 2012-02-10'
echo 'will take several hours'
echo 'socorro can go live again while this is running'
echo 'bug 729195'
psql -f ${CURDIR}/backfill_matviews_for_esr.sql breakpad

#change version in DB
psql -c "SELECT update_socorro_db_version( '$VERSION' )" breakpad

echo "$VERSION upgrade done"

exit 0