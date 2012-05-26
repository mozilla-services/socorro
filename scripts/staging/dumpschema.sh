#!/bin/bash

DB=$1
PORT=$3
: ${DB:="breakpad"}
if [ -z $2 ]
then
	$HOST=''
else
	$HOST=" -h $2" 
fi
: ${PORT:="5432"}

pg_dump $HOST -p $PORT -s -T '*_201*' -T 'priority_jobs_*' $DB > schema.sql

echo 'schema dumped'

exit 0