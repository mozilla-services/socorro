#!/bin/bash

set -e

/etc/init.d/postgresql-9.0 stop

rm -rf /pgdata/backupdata/*

cp -r -p -v /pgdata/9.0/data/* /pgdata/backupdata/

/etc/init.d/postgresql-9.0 start

exit 0