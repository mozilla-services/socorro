#!/bin/sh

TABLES="daily_crash_codes os_names os_name_matches process_types products release_channels product_release_channels raw_adu release_channel_matches releases_raw uptime_levels windows_versions reports os_versions productdims product_productid_map release_repositories crontabber_state"

for table in $TABLES
do
  psql -c "COPY $table FROM '`pwd`/${table}.csv' WITH CSV HEADER" breakpad
  exit_code=$?
  if [ $exit_code != 0 ]
  then
    echo "Failed to import ${table}"
    exit $exit_code
  fi
done

psql -c "SELECT backfill_matviews('2012-05-15', '2012-05-16')" breakpad
psql -c "UPDATE product_versions SET featured_version = true" breakpad
