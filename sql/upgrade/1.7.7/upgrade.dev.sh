#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# update script for test machines for 1.7.6 --> 1.7.7
# only backfills the last few weeks instead of all tables

# DO NOT RUN IN PRODUCTION

set -e

date

export PATH=$PATH

echo 'install citext'
psql -f citext.sql breakpad

echo 'backfill the reason index'
./reason_index.py reports_20110207 reports_20110328

echo 'create the duplicates tables and functions'
psql -f find_dups.sql breakpad
psql -f backfill_dups.sql breakpad

echo 'backfill some duplicates'
./backfill_dups.py '2011-03-15 00:00:00'

echo 'create tk_version function'
psql -f tk_version.sql breakpad

echo 'clean up versions'
psql -f clean_up_versions.sql breakpad

echo 'fill in first reports'
psql -f first_report_migration.dev.sql breakpad

date

exit 0
