#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


TABLES="os_names os_name_matches process_types products release_channels product_release_channels raw_adu release_channel_matches releases_raw uptime_levels windows_versions reports os_versions product_productid_map release_repositories crontabber_state report_partition_info"

function db {
  sql=$1
  psql -c "$sql" breakpad > last_psql.log 2>&1
  exit_code=$?
  if [ $exit_code != 0 ]
  then
    echo "ERROR: SQL failed - $sql"
    cat last_psql.log
    exit $exit_code
  fi
  
  # catch failures from SPs like backfill_matviews
  grep "ERROR" last_psql.log
  if [ $? == 0 ]
  then
    echo "ERROR: error found in output for $sql"
    cat last_psql.log
    exit 1
  fi
}

echo "loading CSVs..."
for table in $TABLES
do
  db "COPY $table FROM '`pwd`/${table}.csv' WITH CSV HEADER"
done

echo "running backfill_matviews..."
db "SELECT backfill_matviews('2012-12-11', '2012-12-12')"
echo "setting all versions to featured..."
db "UPDATE product_versions SET featured_version = true"
echo "Done."
