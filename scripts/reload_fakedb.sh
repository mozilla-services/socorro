#!/bin/bash

source socorro-virtualenv/bin/activate
export PYTHONPATH=.
export PGUSER=$1
export PGPASSWORD=$2
export PGPORT=$3
export PGHOST=$4

#  create empty DB named "fakedata"
# FIXME - setupdb_app doesn't seem to honor psql escape settings, load the old fashioned way for now
#./socorro/external/postgresql/setupdb_app.py --database_name=fakedata --database_password=fakedata --dropdb
dropdb fakedata
createdb fakedata
psql -f sql/schema.sql fakedata > schema.log

# generate fakedata
./socorro/external/postgresql/fakedata.py > load.sql

# load fakedata into DB
psql fakedata < load.sql > load.out

