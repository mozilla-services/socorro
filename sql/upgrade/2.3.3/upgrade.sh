#please see README

set -e

CURDIR=$(dirname $0)

echo 'new support functions, and reload some old ones with code fixes'
psql -f ${CURDIR}/support_functions.sql breakpad
psql -f ${CURDIR}/support_functions_fix.sql breakpad

echo 'os_version_string formatting function and populating os_versions table'
psql -f ${CURDIR}/os_version_string.sql breakpad
psql -f ${CURDIR}/update_os_versions.sql breakpad
psql -f ${CURDIR}/update_os_versions_new_reports.sql breakpad

echo 'fixes for update_products'
psql -f ${CURDIR}/update_products.sql breakpad

echo 'os_version & signature counts'
psql -f ${CURDIR}/os_signature_totals.sql breakpad

echo 'product & signature counts'
psql -f ${CURDIR}/product_signature_counts.sql breakpad

echo 'uptime window & signature counts'
psql -f ${CURDIR}/uptime_signature_counts.sql breakpad

echo 'backfill functions'
psql -f ${CURDIR}/backfill_signature_counts.sql breakpad
psql -f ${CURDIR}/backfill_matviews.sql breakpad

echo 'hang_report should check that reports_clean is done'
psql -f ${CURDIR}/hang_report.sql breakpad

echo 'reports weekly partitioning function'
psql -f ${CURDIR}/reports_weekly_partitioning.sql breakpad

exit 0