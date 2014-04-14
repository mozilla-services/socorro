#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


set -e

cp /pgdata/9.0/data/postgresql.conf.prod /pgdata/9.0/data/postgresql.conf

/etc/init.d/postgresql-9.0 restart

su -l -c "psql -f ~postgres/update_staging_passwords.sql" postgres

/etc/init.d/pgbouncer-web start
/etc/init.d/pgbouncer-processor start

exit 0

