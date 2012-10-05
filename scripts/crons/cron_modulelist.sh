#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


. /etc/socorro/socorrorc

NAME=`basename $0 .sh`
lock $NAME

DATE=`date -d 'yesterday' +%y%m%d`
OUTPUT_DATE=`date -d $DATE +%Y%m%d`
OUTPUT_FILE="/mnt/crashanalysis/crash_analysis/modulelist/modulelist-${OUTPUT_DATE}.txt"

export PIG_CLASSPATH=${SOCORRO_DIR}/analysis/

pig -param start_date=$DATE -param end_date=$DATE ${SOCORRO_DIR}/analysis/modulelist.pig >> /var/log/socorro/cron_modulelist.log 2>&1
fatal $? "pig run failed"

hadoop fs -getmerge modulelist-${DATE}-${DATE} $OUTPUT_FILE
fatal $? "hadoop getmerge failed"

hadoop fs -rmr modulelist-${DATE}-${DATE}
fatal $? "hadoop cleanup failed"

unlock $NAME
