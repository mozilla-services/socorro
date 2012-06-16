#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# update script for 1.7.8 --> 2.0
# suitable for both dev instances and prod

set -e
set -u

date

echo 'create cronjobs table'
psql -f cronjobs.sql

echo 'fix permissions for processor user'
psql -f permissions.sql

date

exit 0
