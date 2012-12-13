#! /bin/bash
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


. /etc/socorro/socorrorc
. /etc/socorro/socorro-monitor.conf

lock cron_libraries
NAME=`basename $0 .sh`
lock $NAME

PGPASSWORD=$databasePassword
export PGPASSWORD

DATE=`date '+%Y%m%d'`
WEEK=`date -d 'last monday' '+%Y%m%d'`

# gnu date does not seem to be able to do 'last monday' with a relative date
if [ -n "$1" ]
then
  DATE=$1
  d=$DATE
  while true
  do
    if [[ "$d" == Mon* ]]
    then
      WEEK=`date -d "$d" '+%Y%m%d'`
      break
    fi
    d=`date -d "$d - 1 day"`
  done
fi

SQL_DATE="date '`date -d "$DATE" '+%Y-%m-%d'`'"

for I in Firefox Thunderbird SeaMonkey Camino
do
  VERSIONS=`psql -t -U $databaseUserName -h $databaseHost $databaseName -c "select version, count(*) as counts from reports_${WEEK}  where completed_datetime < $SQL_DATE and completed_datetime > ($SQL_DATE - interval '24 hours') and product = '${I}' group by version order by counts desc limit 3" | awk '{print $1}'`
  for J in $VERSIONS
  do
    psql -t -U $databaseUserName -h $databaseHost $databaseName -c "select uuid from reports_${WEEK} where completed_datetime < $SQL_DATE and completed_datetime > ($SQL_DATE - interval '24 hours') and product = '${I}' and version = '${J}'" | $PYTHON ${APPDIR}/socorro/external/hbase/hbase_client.py -h $hbaseHost export_jsonz_tarball_for_ooids /tmp /tmp/${I}_${J}.tar > /tmp/${I}_${J}.log 2>&1
    $PYTHON /data/crash-data-tools/per-crash-core-count.py -p ${I} -r ${J} -f /tmp/${I}_${J}.tar > /tmp/${DATE}_${I}_${J}-core-counts.txt
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -p ${I} -r ${J} -f /tmp/${I}_${J}.tar > /tmp/${DATE}_${I}_${J}-interesting-modules.txt
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -v -p ${I} -r ${J} -f /tmp/${I}_${J}.tar > /tmp/${DATE}_${I}_${J}-interesting-modules-with-versions.txt
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -a -p ${I} -r ${J} -f /tmp/${I}_${J}.tar > /tmp/${DATE}_${I}_${J}-interesting-addons.txt
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -v -a -p ${I} -r ${J} -f /tmp/${I}_${J}.tar > /tmp/${DATE}_${I}_${J}-interesting-addons-with-versions.txt
  done
done

MANUAL_VERSION_OVERRIDE="18.0 19.0a2 20.0a1"
for I in Firefox
do
  for J in $MANUAL_VERSION_OVERRIDE
  do
    psql -t -U $databaseUserName -h $databaseHost $databaseName -c "select uuid from reports_${WEEK} where completed_datetime < $SQL_DATE and completed_datetime > ($SQL_DATE - interval '24 hours') and product = '${I}' and version = '${J}'" | $PYTHON ${APPDIR}/socorro/external/hbase/hbase_client.py -h $hbaseHost export_jsonz_tarball_for_ooids /tmp /tmp/${I}_${J}.tar > /tmp/${I}_${J}.log 2>&1
    $PYTHON /data/crash-data-tools/per-crash-core-count.py -p ${I} -r ${J} -f /tmp/${I}_${J}.tar > /tmp/${DATE}_${I}_${J}-core-counts.txt
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -p ${I} -r ${J} -f /tmp/${I}_${J}.tar > /tmp/${DATE}_${I}_${J}-interesting-modules.txt
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -v -p ${I} -r ${J} -f /tmp/${I}_${J}.tar > /tmp/${DATE}_${I}_${J}-interesting-modules-with-versions.txt
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -a -p ${I} -r ${J} -f /tmp/${I}_${J}.tar > /tmp/${DATE}_${I}_${J}-interesting-addons.txt
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -v -a -p ${I} -r ${J} -f /tmp/${I}_${J}.tar > /tmp/${DATE}_${I}_${J}-interesting-addons-with-versions.txt
  done
done

find /tmp -name ${DATE}\* -type f -size +500k | xargs gzip -9
mkdir /mnt/crashanalysis/crash_analysis/${DATE}
cp /tmp/${DATE}* /mnt/crashanalysis/crash_analysis/${DATE}/
rm -f /tmp/${DATE}*

techo "unlock cron_libraries"
unlock $NAME

techo "exit 0"
exit 0
