#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


. /etc/socorro/socorrorc

NAME=`basename $0 .sh`
lock $NAME

DATE=`date -d 'yesterday' +%y%m%d`
OUTPUT_DATE=`date -d $DATE +%Y%m%d`
OUTPUT_DIR="/mnt/crashanalysis/crash_analysis/modulelist/"

ssh $HADOOP_GW "PIG_CLASSPATH=./socorro/analysis pig -param start_date=$DATE -param end_date=$DATE ./socorro/analysis/modulelist.pig" >> /var/log/socorro/cron_modulelist.log 2>&1
fatal $? "pig run failed"

ssh $HADOOP_GW "hadoop fs -getmerge modulelist-${DATE}-${DATE} ${OUTPUT_DATE}-modulelist.txt" >> /var/log/socorro/cron_modulelist.log 2>&1
fatal $? "hadoop getmerge failed"

scp $HADOOP_GW:${OUTPUT_DATE}-modulelist.txt $OUTPUT_DIR >> /var/log/socorro/cron_modulelist.log 2>&1
fatal $? "scp from gw to output dir failed"

ssh $HADOOP_GW "hadoop fs -rmr modulelist-${DATE}-${DATE}" >> /var/log/socorro/cron_modulelist.log 2>&1
fatal $? "hadoop cleanup failed"

unlock $NAME
