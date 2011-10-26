#!/bin/bash

set -e

/etc/init.d/postgresql-90 stop

set +e
rm -rf /pgdata/backupdata
set -e

cp -r -p /data/pglocaldata/data /pgdata/backupdata

/etc/init.d/postgresql-90 start

exit 0