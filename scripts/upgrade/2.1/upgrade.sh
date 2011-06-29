#!/bin/bash

# update script for 2.0 --> 2.1
# suitable for both dev instances and prod 

set -e
set -u

date

echo 'create objects for correlation reports'
psql -f correlation_reports.sql

date

exit 0
