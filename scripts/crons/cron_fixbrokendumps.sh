#!/bin/bash

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
