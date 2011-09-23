#!/bin/bash

set -e
date

echo 'add new support functions'
psql -f support_functions.sql breakpad

echo 'fix case sensitivity issues'
psql -f fix_case_sensitive_matviews.sql breakpad

echo 'new version of update_products'
psql -f update_products.sql breakpad

echo 'create backfill functions'
psql -f backfill_adu.sql breakpad
psql -f backfill_daily_crashes.sql breakpad
psql -f backfill_tcbs.sql breakpad
psql -f backfill_matviews.sql breakpad

echo 'clean up product definitions and backfill all matviews.  will take a while (up to a few hours)'

psql -f clear_out_final_betas.sql breakpad

echo '2.2.3. upgrade done'

date

exit 0
