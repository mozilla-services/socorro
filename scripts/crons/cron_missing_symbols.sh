#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

. /etc/socorro/socorrorc

NAME=`basename $0 .sh`
lock $NAME

DATE=`date -d 'yesterday' +%y%m%d`
OUTPUT_DATE=`date -d $DATE +%Y%m%d`
OUTPUT_DIR="/mnt/crashanalysis/crash_analysis/${OUTPUT_DATE}"
OUTPUT_FILE="${OUTPUT_DATE}-missing-symbols.txt"
read -d '' SQL << EOF
COPY
 (SELECT debug_file, debug_id
 FROM missing_symbols WHERE
 date_processed='${OUTPUT_DATE}'
 AND debug_file != ''
 AND debug_id != ''
 GROUP BY debug_file, debug_id
 )
TO STDOUT WITH CSV HEADER
EOF

export PGPASSWORD=$databasePassword
psql -U $databaseUserName -h $databaseHost $databaseName \
        -c "$SQL" > ${OUTPUT_DIR}/${OUTPUT_FILE}
fatal $? "psql failed"

unlock $NAME
