#!/bin/bash

DB=$1
PORT=$3
: ${DB:="breakpad"}
if [ -z $2 ]
then
        HOST=''
else
        HOST=" -h $2" 
fi
: ${PORT:="5432"}

pg_dump $HOST -p $PORT -s \
    -n public \
	-T high_load_temp \
	-T locks* \
	-T activity_snapshot \
	-T product_info_changelog \
	-T '*_201*' \
	-T 'priority_jobs_*' \
	$DB > schema-20121008.sql

echo 'schema dumped'

exit 0
