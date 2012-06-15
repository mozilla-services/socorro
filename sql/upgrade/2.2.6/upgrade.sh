#!/bin/bash

set -e
date

echo 'correct edit_product_info for aurora/nightly'
psql -f fix_edit_product_info.sql breakpad

echo 'remove tables use in migration to new data center'
psql -f remove_server_migration_tables.sql breakpad

echo 'remove depreciated top url matview'
psql -f remove_topurlcrashreports.sql breakpad

echo 'grant read-only access to all tables to metrics user'
psql -f grant_ro_metrics_access.sql breakpad

echo '2.2.6. upgrade done'

date

exit 0
