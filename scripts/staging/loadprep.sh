#!/bin/bash

set -e

/etc/init.d/pgbouncer-web stop
/etc/init.d/pgbouncer-processor stop

cp /pgdata/9.0/data/postgresql.conf.localonly /pgdata/9.0/data/postgresql.conf

/etc/init.d/postgresql-9.0 restart

exit 0

