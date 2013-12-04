# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Pull raw, unprocessed crashes from an existing Socorro install
# and re-submit to an existing (dev, staging) instance elsewhere.

# Import settings
. /etc/socorro/socorrorc
export PGPASSWORD=$databasePassword

if [ $# != 2 ]
then
    echo "Syntax: cron_submitter.sh <crash_reports_url> <number_to_submit>"
    exit 1
fi

CRASH_REPORTS_HOST=$1
CRASH_REPORT_URL="https://$CRASH_REPORTS_HOST/submit"
LOCK="/var/tmp/$CRASH_REPORTS_HOST.lock"
LOG="/var/log/socorro/cron_submitter-$CRASH_REPORTS_HOST.log"
NUM_TO_SUBMIT=$2

function submit_dump() {

    # Override Hbase settings on admin box
    . /etc/socorro/socorro-monitor.conf
    OOID=$1

    date
    echo $OOID
    ${PYTHON} ${APPDIR}/socorro/external/hbase/hbase_client.py -h $hbaseHost get_json $OOID > /tmp/$OOID.json
    ${PYTHON} ${APPDIR}/socorro/external/hbase/hbase_client.py -h $hbaseHost get_dump $OOID > /tmp/$OOID.dump
    ${PYTHON} ${APPDIR}/socorro/collector/submitter.py -j /tmp/$OOID.json -d /tmp/$OOID.dump -u $CRASH_REPORT_URL
    rm -f /tmp/$OOID.json /tmp/$OOID.dump
}

(
if $(flock -n 200)
then
    SQL="SELECT uuid FROM raw_crashes WHERE (date_processed >= (now() - '5 min'::interval)) AND date_processed < now() ORDER BY date_processed DESC LIMIT $NUM_TO_SUBMIT"
    UUIDS=$(psql -t -U $databaseUserName -h $databaseHost $databaseName -c "$SQL" | tr -d '^ ')

    if [ -z "$UUIDS" ]
    then
        date >> $LOG 2>&1
        echo "SQL query returned no UUIDs." >> $LOG 2>&1
    else
        for UUID in ${UUIDS[@]}
        do
            submit_dump $UUID >> $LOG 2>&1
            sleep 1
        done
    fi
fi
) 200>$LOCK
