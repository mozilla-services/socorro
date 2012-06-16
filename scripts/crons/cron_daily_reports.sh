#!/bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


. /etc/socorro/socorrorc

NAME=`basename $0 .sh`
lock $NAME
SCRIPT_RUN_DATE=`date -d "1 days ago" '+%Y-%m-%d'`
$PYTHON ${APPDIR}/scripts/startDailyUrl.py --day=${SCRIPT_RUN_DATE}
fatal $? "Could not run startDailyUrl"

PUB_DATA_FILE=`date -d "1 days ago" '+%Y%m%d-pub-crashdata.csv.gz'`
SCRIPT_RUN_DATE=`date -d "1 days ago" '+%Y%m%d'`
scp ${PUB_DATA_FILE} ${PUB_USER}@${PUB_SERVER}:${PUB_LOCATION}/${SCRIPT_RUN_DATE}/
EXIT_CODE=$((EXIT_CODE+$?))
mv ${HOME}/${DATA_FILE} /tmp

PRIV_DATA_FILE=`date -d "1 days ago" '+%Y%m%d-crashdata.csv.gz'`
scp ${PRIV_DATA_FILE} ${PRIV_USER}@${PRIV_SERVER}:${PRIV_LOCATION}/
EXIT_CODE=$((EXIT_CODE+$?))
ssh ${PRIV_USER}@${PRIV_SERVER} "chmod 640 ${PRIV_LOCATION}/*"
EXIT_CODE=$((EXIT_CODE+$?))
mv ${HOME}/${DATA_FILE} /tmp

unlock $NAME

if [ "$EXIT_CODE" != 0 ]
then
  echo "ERROR: problems copying files"
  exit 1
fi

