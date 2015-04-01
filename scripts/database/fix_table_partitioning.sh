#!/bin/bash

set -e
set -o xtrace

tablename=$1
# dump the table

pg_dump breakpad \
    -a \
    -t ${tablename} \
    -f ${tablename}.dump 

# break up the files
python partition_dump.py ${tablename}.dump

# Load up the files!
python load_and_check_partition_data.py ${tablename}
