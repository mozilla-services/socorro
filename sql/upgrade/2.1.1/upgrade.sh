#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


# update script for 2.1 --> 2.2
# suitable for both dev instances and prod

set -e
set -u

date

echo 'add releasechannel column to reports table'
./add_releasechannel.py

date

exit 0
