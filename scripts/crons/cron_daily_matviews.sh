#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## NOTE! This is deprecated and obsolete once
## https://bugzilla.mozilla.org/show_bug.cgi?id=761650
## is resolved and fully implemented

. /etc/socorro/socorrorc

NAME=`basename $0 .sh`
lock $NAME
pyjob $NAME startDailyMatviews
EXIT_CODE=$?
unlock $NAME

exit $EXIT_CODE
