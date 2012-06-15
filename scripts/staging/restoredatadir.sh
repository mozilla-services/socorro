#!/bin/bash

set -e

/etc/init.d/postgresql-9.0 stop

rm -rf /pgdata/9.0/data/*

cp -r -p -v /pgdata/backupdata/* /pgdata/9.0/data/ 

/etc/init.d/postgresql-9.0 start

exit 0