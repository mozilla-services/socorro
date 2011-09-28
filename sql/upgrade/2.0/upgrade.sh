#!/bin/bash

# update script for 1.7.8 --> 2.0
# suitable for both dev instances and prod

set -e
set -u

date

echo 'create cronjobs table'
psql -f cronjobs.sql

echo 'fix permissions for processor user'
psql -f permissions.sql

date

exit 0
