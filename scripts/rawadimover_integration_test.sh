#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# This is an integration test for the RawADIMoverCronApp. This test
# must be run by hand in a local development environment.
#
# To run it, first add this to your ``my.env`` file:
#
# crontabber.jobs=socorro.cron.crontabber_app.STAGE_NEW_JOBS
#
# Then do:
#
# ./scripts/rawadimover_integration_test.sh
#
# While you're doing that, open it up in an editor and follow along. You'll know
# when to turn the page when you hear Lonnen yell like this: YARGGH!!!

set -e

# Figure out yesterday's date.
DATE=$(date --utc --date="-1 days" +%Y-%m-%d)

echo "Using date ${DATE}"

# Create three records--two for the day that we're looking for, and one for
# another day that we're not.
SQLDATA=`cat <<EOF
INSERT INTO raw_adi (
    adi_count,
    date,
    product_name,
    product_os_platform,
    product_os_version,
    product_version,
    build,
    product_guid,
    update_channel
)
VALUES (
    15471,
    '${DATE}',
    'Firefox',
    'Darwin',
    '16.7.0',
    '57.0',
    '20171112125346',
    'ec8030f7-c20a-464f-9b0e-13a3a9e97384',
    'release'
), (
    20104,
    '${DATE}',
    'Firefox',
    'Windows_NT',
    '6.3',
    '58.0',
    '20171127135700',
    'ec8030f7-c20a-464f-9b0e-13a3a9e97384',
    'beta'
), (
    1464,
    '2017-12-04',
    'Firefox',
    'Darwin',
    '17.2.0',
    '58.0',
    '20171123161455',
    'ec8030f7-c20a-464f-9b0e-13a3a9e97384',
    'beta'
);
EOF`


echo ""
echo "==============="
echo "Test 1: Dry run"
echo "==============="
echo ""

# Wipe the table
docker-compose exec postgresql psql -U postgres breakpad -c "TRUNCATE raw_adi;"

# Insert some raw_adi data into postgres of the source db
docker-compose exec postgresql psql -U postgres breakpad -c "$SQLDATA"

# Reset the crontabber state for the job ignoring any error code
docker-compose run crontabber ./socorro/cron/crontabber_app.py \
               --reset-job=fetch-adi-from-hive || true

# Run the job as a dry run--it should print out two rows
docker-compose run crontabber ./socorro/cron/crontabber_app.py \
               --job=fetch-adi-from-hive \
               --crontabber.class-RawADIMoverCronApp.dry_run

echo ""
echo "Verify: Should have said it would have inserted two row."


echo ""
echo "==============================================="
echo "Test 2: run for reals, but source_db == dest_db"
echo "==============================================="
echo ""

# Reset the crontabber state for the job ignoring any error code
docker-compose run crontabber ./socorro/cron/crontabber_app.py \
               --reset-job=fetch-adi-from-hive || true

# Run the job
docker-compose run crontabber ./socorro/cron/crontabber_app.py \
               --job=fetch-adi-from-hive

# Since the source and dest were the same, we inserted the two raw_adi rows into
# the souce db, so now they're in there twice
echo ""
echo "Verify: Data in breakpad--should be five rows; two sets of duplicates:"
docker-compose exec postgresql psql -U postgres breakpad -c "SELECT * FROM raw_adi;"


echo ""
echo "======================================="
echo "Test 3: Different source_db and dest_db"
echo "======================================="
echo ""

# Wipe the table and insert the raw_adi in again
docker-compose exec postgresql psql -U postgres breakpad -c "TRUNCATE raw_adi;"
docker-compose exec postgresql psql -U postgres breakpad2 -c "TRUNCATE raw_adi;" || true
docker-compose exec postgresql psql -U postgres breakpad -c "$SQLDATA"

# Set up a second db
# This will prompt you to say "y". Sorry about that.
docker-compose run -e DATASERVICE_DATABASE_NAME=breakpad2 webapp ./docker/run_setup_postgres.sh

# Reset the crontabber state for the job ignoring any error code
docker-compose run crontabber ./socorro/cron/crontabber_app.py \
               --reset-job=fetch-adi-from-hive || true

# Run the job with source_db != dest_db
docker-compose run crontabber ./socorro/cron/crontabber_app.py \
               --job=fetch-adi-from-hive \
               --crontabber.class-RawADIMoverCronApp.destination.database_name=breakpad2

echo ""
echo "Verify: Data in breakpad--should be three rows:"
docker-compose exec postgresql psql -U postgres breakpad -c "SELECT * FROM raw_adi;"

echo ""
echo "Verify: Data in breakpad2--should be two rows:"
docker-compose exec postgresql psql -U postgres breakpad2 -c "SELECT * FROM raw_adi;"
