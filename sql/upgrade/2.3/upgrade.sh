#!/bin/bash

set -e
date

echo 'add new hang/crash report stored procedure and matview'
psql -f hang_report.sql breakpad

echo 'backfill last two weeks'
psql -f backfill_hangreport.sql breakpad
BEGIN=`date --date '15 days ago' +%Y-%m-%d`
END=`date --date 'yesterday' +%Y-%m-%d`
psql -c "select backfill_hangreport('$BEGIN', '$END')"

echo '2.3 upgrade done'

date

exit 0
