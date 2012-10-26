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

pg_dump $HOST -p $PORT -s -U postgres -T '*_201*' -T 'priority_jobs_*' $DB > schema-20121008.sql

echo 'CREATE EXTENSION citext from unpackaged;' >> schema-20121008.sql

echo 'schema dumped'

exit 0
