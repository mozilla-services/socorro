#!/bin/bash

. /etc/socorro/socorrorc

NAME=`basename $0 .sh`
lock $NAME
DATE=`date -d 'yesterday' +%Y%m%d`
${SOCORRO_DIR}/analysis/modulelist.sh Firefox "Windows NT" $DATE >> /var/log/socorro/cron_modulelist.log 2>&1
EXIT_CODE=$?
unlock $NAME

exit $EXIT_CODE
