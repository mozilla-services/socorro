#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


. /etc/socorro/socorrorc

NAME=`basename $0 .sh`

# TODO this needs to stay in sync with the correlations.pig script
# FIXME move this bit to pig when we switch to 0.9 and use the new PigStorage
COLUMNS="filename,debug_file,debug_id,module_version,product,version,os_name,reason"
DATE=`date -d 'yesterday' +%y%m%d`
OUTPUT_DATE=`date -d $DATE +%Y%m%d`
OUTPUT_FILE="/mnt/crashanalysis/crash_analysis/correlations/correlations-${OUTPUT_DATE}.txt"
lock $NAME

pig -param start_date=$DATE -param end_date=$DATE ${SOCORRO_DIR}/analysis/correlations.pig >> /var/log/socorro/cron_correlations.log 2>&1
fatal $? "pig run failed"

TMPFILE=`mktemp`
echo $COLUMNS > $TMPFILE
fatal $? "could not write header to tmpfile"

hadoop fs -cat correlations-${DATE}-${DATE} >> $TMPFILE
fatal $? "hadoop cat failed writing to tmpfile"

cat $OUTPUT_FILE | psql -U $databaseUserName -h $databaseHost $databaseName -c 'COPY correlations_raw FROM STDIN WITH CSV HEADER'
fatal $? "writing correlations to DB failed"

mv $TMPFILE $OUTPUT_FILE
fatal $? "could not move tmpfile to output dir"

hadoop fs -rmr correlations-${DATE}-${DATE}
fatal $? "hadoop cleanup failed"

unlock $NAME
