#!/bin/bash

DB=$1
USER=$2
PORT=$4
: ${USER:="postgres"}
: ${DB:="breakpad"}
if [ -z $3 ]
then
        HOST=''
else
        HOST=" -h $2" 
fi
: ${PORT:="5432"}

TODAY=`date +%Y%m%d`

pg_dump $HOST -p $PORT -s -U $USER \
	-T high_load_temp \
	-T locks* \
	-T activity_snapshot \
	-T product_info_changelog \
	-T '*_201*' \
	-T 'priority_jobs_*' \
	$DB > schema-$DB-$TODAY.sql

echo 'schema dumped'

exit 0
