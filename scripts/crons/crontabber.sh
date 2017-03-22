#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


. /etc/socorro/socorrorc

NAME=`basename $0 .sh`
CT_INI="/etc/socorro/crontabber.ini"
export CMD="${PYTHON} ${APPDIR}/socorro/cron/crontabber_app.py"
LOG=/var/log/socorro/crontabber.log
if [ -f $CT_INI ] && [ -r $CT_INI ]; then
    $CMD --admin.conf=$CT_INI >> $LOG 2>&1
else
    envconsul -once -prefix socorro/common -prefix socorro/crontabber bash -c "$CMD" >> $LOG 2>&1
fi
EXIT_CODE=$?

exit $EXIT_CODE
