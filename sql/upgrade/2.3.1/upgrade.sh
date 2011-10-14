#!/bin/bash

#please see README

set -e

CURDIR=$(dirname $0)

echo 'alter the releases_raw table so that it can accept nightlies'
psql -f ${CURDIR}/alter_releases_raw.sql breakpad

echo 'update products now with aurora and nightlies'
psql -f ${CURDIR}/update_products.sql breakpad

echo 'create table if not exists function'
psql -f ${CURDIR}/create_table_if_not_exists.sql breakpad

echo 'new support functions, mostly timestamp conversion'
psql -f ${CURDIR}/support_functions.sql breakpad

echo 'new tables for reports_clean'
psql -f ${CURDIR}/reports_clean_new_tables.sql breakpad

echo 'lookup list populating function'
psql -f ${CURDIR}/insert_into_lookup_lists.sql breakpad

echo 'adjust reports_duplicates to make it faster'
psql -f ${CURDIR}/update_reports_duplicates.sql breakpad

echo 'os_versions function for reports_clean'
psql -f ${CURDIR}/update_os_versions_new_reports.sql breakpad

echo 'partition manager for reports_clean'
psql -f ${CURDIR}/reports_clean_weekly.sql breakpad

echo 'update function for reports_clean'
psql -f ${CURDIR}/alter_releases_raw.sql breakpad

echo 'backfill function for reports clean'
psql -f ${CURDIR}/backfill_reports_clean.sql breakpad

echo 'fix gap in backfill_matviews'
psql -f ${CURDIR}/backfill_matviews.sql breakpad

echo 'add hang reports'
psql -f ${CURDIR}/hang_report.sql breakpad

echo 'now backfill data back to 9/1.  This will take hours'
psql -f ${CURDIR}/backfill_everything.sql breakpad


exit 0
