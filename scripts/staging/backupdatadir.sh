#!/bin/bash

set -e

/etc/init.d/postgresql-9.0 stop

set +e
rm -rf /pgdata/backupdata
set -e

cp -r -p /data/pglocaldata/data /pgdata/backupdata

/etc/init.d/postgresql-9.0 start

exit 0