#!/bin/bash

set -e

cp /pgdata/9.0/data/postgresql.conf.prod /pgdata/9.0/data/postgresql.conf

/etc/init.d/postgresql-90 restart

su -l -c "psql -f ~postgres/update_staging_passwords.sql" postgres

/etc/init.d/pgbouncer-web start
/etc/init.d/pgbouncer-processor start

exit 0

