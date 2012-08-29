#! /bin/sh
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


. /etc/socorro/socorrorc
. /etc/socorro/socorro-monitor.conf
PGPASSWORD=$databasePassword
export PGPASSWORD

WEEK=`date -d 'last monday' '+%Y%m%d'`
DATE=`date '+%Y%m%d'`
for I in Firefox Thunderbird SeaMonkey Camino
do
  VERSIONS=`psql -t -U $databaseUserName -h $databaseHost $databaseName -c "select version, count(*) as counts from reports_${WEEK}  where completed_datetime < NOW() and completed_datetime > (NOW() - interval '24 hours') and product = '${I}' group by version order by counts desc limit 3" | awk '{print $1}'`
  for J in $VERSIONS
  do
    psql -t -U $databaseUserName -h $databaseHost $databaseName -c "select uuid from reports_${WEEK} where completed_datetime < NOW() and completed_datetime > (NOW() - interval '24 hours') and product = '${I}' and version = '${J}'" | $PYTHON ${APPDIR}/socorro/storage/hbaseClient.py -h $hbaseHost export_jsonz_tarball_for_ooids /tmp /tmp/${I}_${J}.tar > /tmp/${I}_${J}.log 2>&1
    $PYTHON /data/crash-data-tools/per-crash-core-count.py -p ${I} -r ${J} -f /tmp/${I}_${J}.tar > /tmp/${DATE}_${I}_${J}-core-counts.txt
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -p ${I} -r ${J} -f /tmp/${I}_${J}.tar > /tmp/${DATE}_${I}_${J}-interesting-modules.txt
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -v -p ${I} -r ${J} -f /tmp/${I}_${J}.tar > /tmp/${DATE}_${I}_${J}-interesting-modules-with-versions.txt
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -a -p ${I} -r ${J} -f /tmp/${I}_${J}.tar > /tmp/${DATE}_${I}_${J}-interesting-addons.txt
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -v -a -p ${I} -r ${J} -f /tmp/${I}_${J}.tar > /tmp/${DATE}_${I}_${J}-interesting-addons-with-versions.txt
  done
done

MANUAL_VERSION_OVERRIDE="16.0 17.0a2 18.0a1"
for I in Firefox
do
  for J in $MANUAL_VERSION_OVERRIDE
  do
    psql -t -U $databaseUserName -h $databaseHost $databaseName -c "select uuid from reports_${WEEK} where completed_datetime < NOW() and completed_datetime > (NOW() - interval '24 hours') and product = '${I}' and version = '${J}'" | $PYTHON ${APPDIR}/socorro/storage/hbaseClient.py -h $hbaseHost export_jsonz_tarball_for_ooids /tmp /tmp/${I}_${J}.tar > /tmp/${I}_${J}.log 2>&1
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

