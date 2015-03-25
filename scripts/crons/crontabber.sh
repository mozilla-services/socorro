#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


. /etc/socorro/socorrorc

NAME=`basename $0 .sh`
lock --ignore-existing $NAME
CMD="${PYTHON} ${APPDIR}/socorro/cron/crontabber_app.py"
LOG=/var/log/socorro/crontabber.log
if [ -f "/etc/socorro/crontabber.ini" ]; then
    $CMD --admin.conf=/etc/socorro/crontabber.ini >> $LOG 2>&1
else
    $CMD >> $LOG 2>&1
fi
EXIT_CODE=$?
unlock $NAME

exit $EXIT_CODE
