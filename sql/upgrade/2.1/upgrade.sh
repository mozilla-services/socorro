#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# update script for 2.0 --> 2.1
# suitable for both dev instances and prod

set -e
set -u

date

#correlation reports not included for now; maybe in 2.2
#echo 'create objects for correlation reports'
#psql -f correlation_reports.sql

echo 'fix permissions for breakpad_ro'
psql -f breakpad_ro_perms.sql breakpad

date

exit 0
