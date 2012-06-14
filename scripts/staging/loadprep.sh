#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


set -e

/etc/init.d/pgbouncer-web stop
/etc/init.d/pgbouncer-processor stop

cp /pgdata/9.0/data/postgresql.conf.localonly /pgdata/9.0/data/postgresql.conf

/etc/init.d/postgresql-9.0 restart

exit 0

