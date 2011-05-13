#!/bin/bash

# update script for 1.7.7 --> 1.7.8
# suitable for both dev instances and prod 

set -e

date

echo 'drop the extensions index'
./drop_extenstions_index.py

echo 'drop the duplicate uuid index'
./drop_reports_uuid_index.py

echo 'add the new pgbouncer config.  this will interrupt service'
./pgbouncer_processor_pool.sh

date

exit 0
