#!/bin/bash

#please see README

set -e

CURDIR=$(dirname $0)

echo 'add function for content crash count'
psql -f ${CURDIR}/content_count_state.sql breakpad

echo 'update products now with aurora and nightlies'
psql -f ${CURDIR}/update_products.sql breakpad

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
psql -f ${CURDIR}/update_reports_clean.sql breakpad

echo 'backfill function for reports clean'
psql -f ${CURDIR}/backfill_reports_clean.sql breakpad

echo 'remove tcbs_ranking from update_tcbs.sql'
psql -f ${CURDIR}/update_tcbs.sql breakpad

echo 'fix gap in backfill_matviews'
psql -f ${CURDIR}/backfill_matviews.sql breakpad

echo 'add hang reports'
psql -f ${CURDIR}/hang_report.sql breakpad

echo 'update product views'
psql -f ${CURDIR}/product_views.sql breakpad

echo 'fix adu for nightly/aurora'
psql -f ${CURDIR}/daily_adu.sql breakpad

echo 'fix daily crashes for nightly/aurora'
psql -f ${CURDIR}/daily_crashes.sql breakpad

echo 'add functions for purging old partitions'
psql -f ${CURDIR}/datapurge.sql breakpad

echo 'now backfill data back to 9/1.  This will take hours'
psql -f ${CURDIR}/backfill_everything.sql breakpad


exit 0
