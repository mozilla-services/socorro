#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


TABLES="os_names os_name_matches process_types products release_channels product_release_channels raw_adu release_channel_matches releases_raw uptime_levels windows_versions reports os_versions product_productid_map release_repositories crontabber_state report_partition_info"

if [ -z "$DB_HOST" ]
then
  DB_HOST="localhost"
fi

if [ -z "$DB_USER" ]
then
  DB_USER="breakpad_rw"
fi

if [ -z "$DB_PASSWORD" ]
then
  DB_PASSWORD="aPassword"
fi

function db {
  sql=$1
  export PGPASSWORD=$DB_PASSWORD
  psql -U $DB_USER -h $DB_HOST -c "$sql" breakpad > import.log 2>&1
  exit_code=$?
  if [ $exit_code != 0 ]
  then
    echo "ERROR: SQL failed - $sql"
    cat import.log
    exit $exit_code
  fi
  
  # catch failures from SPs like backfill_matviews
  grep "ERROR" import.log
  if [ $? == 0 ]
  then
    echo "ERROR: error found in output for $sql"
    cat import.log
    exit 1
  fi
}

echo "loading CSVs..."
for table in $TABLES
do
  cat $PWD/tools/dataload/${table}.csv | db "COPY $table FROM STDIN WITH CSV HEADER"
done

echo "running backfill_matviews..."
db "SELECT backfill_matviews('2012-12-11', '2012-12-12')"
echo "setting all versions to featured..."
db "UPDATE product_versions SET featured_version = true"
echo "Done."
