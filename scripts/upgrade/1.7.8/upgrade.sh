#!/bin/bash

# update script for 1.7.7 --> 1.7.8
# suitable for both dev instances and prod 

set -e
set -u

# NEWPW=$1

date

echo 'drop the extensions index'
./drop_extenstions_index.py

echo 'drop the duplicate uuid index'
./drop_reports_uuid_index.py

#removed since it's already been deployed
#echo 'add the new pgbouncer config.  this will interrupt service'
#./pgbouncer_processor_pool.py $NEWPW

date

exit 0
