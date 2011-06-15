#!/bin/bash

# update script for 1.7.8 --> 2.0
# suitable for both dev instances and prod 

set -e
set -u

date

echo 'create the cronjobs table'
psql -f cronjobs.sql breakpad

echo 'create objects for correlation reports'
psql -f correlation_reports.sql

date

exit 0
