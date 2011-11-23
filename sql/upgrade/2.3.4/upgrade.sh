#please see README

set -e

CURDIR=$(dirname $0)

echo 'add version_sort to all product views for sorting'
echo 'bug 703416'
psql -f ${CURDIR}/version_sort_prep.sql breakpad
psql -f ${CURDIR}/product_views.sql breakpad

echo 'add logging to product editing'
echo 'bug 697669'
psql -f ${CURDIR}/edit_product_info_log.sql breakpad

echo 'switch tcbs and daily_crashes to using reports_clean'
echo 'bug 701255'
psql -f ${CURDIR}/update_tcbs.sql breakpad
psql -f ${CURDIR}/daily_crashes.sql breakpad
psql -f ${CURDIR}/backfill_matviews.sql breakpad

echo 'add automated trimming of reports_bad'
echo 'bug 703429'
psql -f ${CURDIR}/update_reports_clean.sql breakpad
psql -f ${CURDIR}/truncate_reports_bad.sql breakpad

echo 'fix tz conversion functions'
echo 'bug 703731'
psql -f ${CURDIR}/fix_tz_functions.sql breakpad

echo 'fix reports_clean to include corrupt dumps'
echo 'bug 704630'
psql -f ${CURDIR}/unknown.sql breakpad
psql -f ${CURDIR}/update_reports_clean.sql breakpad

exit 0