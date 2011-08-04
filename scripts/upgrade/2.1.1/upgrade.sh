#!/bin/bash

# update script for 2.1 --> 2.2
# suitable for both dev instances and prod 

set -e
set -u

date

echo 'add releasechannel column to reports table'
./add_releasechannel.py

date

exit 0
