#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


set -e

/etc/init.d/postgresql-9.0 stop

rm -rf /pgdata/9.0/data/*

cp -r -p -v /pgdata/backupdata/* /pgdata/9.0/data/ 

/etc/init.d/postgresql-9.0 start

exit 0