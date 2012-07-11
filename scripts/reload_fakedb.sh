#!/bin/sh

source socorro-virtualenv/bin/activate
export PYTHONPATH=.

# create empty DB named "fakedata"
./socorro/external/postgresql/setupdb_app.py --database_name=fakedata --database_password=fakedata --dropdb

# generate fakedata
./socorro/external/postgresql/fakedata.py > load.sql

# load fakedata into DB
psql fakedata < load.sql > load.out
