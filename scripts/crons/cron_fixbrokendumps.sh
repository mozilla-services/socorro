#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


. /etc/socorro/socorrorc
# Mozilla PHX needs this because of the particular VLAN setup there
# TODO - give cron jobs their own config overrides
. /etc/socorro/socorro-monitor.conf

NAME=`basename $0 .sh`
lock $NAME
pyjob $NAME startFixBrokenDumps
EXIT_CODE=$?
unlock $NAME

exit $EXIT_CODE
