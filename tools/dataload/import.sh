#!/bin/sh
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


TABLES="os_names os_name_matches process_types products release_channels product_release_channels raw_adu release_channel_matches releases_raw uptime_levels windows_versions reports os_versions product_productid_map release_repositories crontabber_state"

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

psql -c "SELECT backfill_matviews('2012-06-15', '2012-06-16')" breakpad
psql -c "UPDATE product_versions SET featured_version = true" breakpad
