#!/bin/bash

# update script for 2.1 --> 2.2
# suitable for both dev instances and prod

set -e
set -u

date

#release channel was added ahead of time, since it needs to be backfilled
#echo 'add releasechannel column to reports table'
#./add_releasechannel.py

#backfilling is also done offline, because it takes so long
#echo 'backfilling release_channel'
#./releasechannel_backfill.py

#also loaded in advance
#echo 'new release and adu tables'
psql -f raw_adu.sql breakpad
psql -f releases_raw.sql breakpad

echo 'load support functions'
psql -f support_functions.sql breakpad

echo 'load new tables'
psql -f new_tcbs_tables.sql breakpad
ADU
echo 'load product information'
psql -f product_migration.sql breakpad

echo 'load OS information'
psql -f os_migration.sql breakpad

echo 'load signature information'
psql -f signature_migration.sql breakpad

echo 'ADU update functions'
psql -f daily_adu.sql breakpad

echo 'new TCBS building functions and backfilling tcbs (takes a while)'
psql -f update_tcbs.sql breakpad

echo 'new daily_crashes cron job'
psql -f daily_crashes.sql breakpad

echo 'new edit_product_info admin function'
psql -f edit_product_info.sql

date

exit 0
