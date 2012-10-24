#!/bin/bash

for i in 319793 319794 ; do
	psql -A -t breakpad -c " SELECT pg_catalog.pg_get_functiondef($i);" -o backfill_one_day_$i.sql
done

for i in `cat functions.txt`; do
	psql -A -t breakpad -c " SELECT pg_catalog.pg_get_functiondef('$i'::regproc);" -o $i.sql
done
