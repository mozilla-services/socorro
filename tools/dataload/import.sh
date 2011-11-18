#!/bin/sh

TABLES="daily_crash_codes os_names os_name_matches process_types products release_channels product_release_channels raw_adu release_channel_matches releases_raw uptime_levels windows_versions reports os_versions productdims"

for table in $TABLES
do
  psql -c "COPY $table FROM '`pwd`/${table}.csv' WITH CSV HEADER" breakpad
done
