# Import settings
. /etc/socorro/socorrorc

CRASH_REPORTS_HOST=$1
CRASH_REPORT_URL="https://$CRASH_REPORTS_HOST/submit"
LOCK="/var/tmp/$CRASH_REPORTS_HOST.lock"
LOG="/tmp/submit_$CRASH_REPORTS_HOST.log"
NUM_TO_SUBMIT=$2

function submit_dump() {

    # Override Hbase settings on admin box
    . /etc/socorro/socorro-monitor.conf
    OOID=$1

    python ${APPDIR}/socorro/storage/hbaseClient.py -h $hbaseHost get_json $OOID > /tmp/$OOID.json
    python ${APPDIR}/socorro/storage/hbaseClient.py -h $hbaseHost get_dump $OOID > /tmp/$OOID.dump
    python ${APPDIR}/socorro/collector/submitter.py -j /tmp/$OOID.json -d /tmp/$OOID.dump -u $CRASH_REPORT_URL
    rm -f /tmp/$OOID.json /tmp/$OOID.dump
}

( 
if $(flock -n 200)
then
    SQL="SELECT uuid FROM jobs ORDER BY queueddatetime DESC LIMIT $NUM_TO_SUBMIT"
    UUIDS=$(psql -t -U $databaseUserName -h $databaseHost $databaseName -c "$SQL" | tr -d '^ ')

    for UUID in ${UUIDS[@]}
    do
        submit_dump $UUID
        sleep 1
    done 
fi
) 200>$LOCK

