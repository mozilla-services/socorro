#!/bin/sh

cd /home/rhelmer/dev/socorro
source socorro-virtualenv/bin/activate

#  create empty DB named "fakedata"
# FIXME - setupdb_app doesn't seem to honor psql escape settings, load the old fashioned way for now
#./socorro/external/postgresql/setupdb_app.py --database_name=fakedata --database_password=fakedata --dropdb
dropdb fakedata
createdb fakedata
psql -f sql/schema.sql fakedata > schema.log
./socorro/external/postgresql/fakedata.py > load.sql
export PGPASSWORD=fakedata
#psql -U fakedata -p 4321 -h 10.8.70.124 fakedata < load.sql > load.out 2>&1
psql -U fakedata -h localhost fakedata < load.sql > load.out 2>&1
grep ERROR load.out
