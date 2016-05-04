#!/bin/bash -x
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# techo is echo, but with a timestamp
function techo(){
  STAMP="[`date -u +'%F %T'`]"
  echo "$STAMP $1"
}

. /etc/socorro/socorrorc

techo "lock cron_libraries"
NAME=`basename $0 .sh`
lock $NAME

PGPASSWORD=$SECRETS_POSTGRESQL_DATABASE_PASSWORD
export PGPASSWORD

DATE=`date '+%Y%m%d'`
WEEK=`date -d 'last monday' '+%Y%m%d'`

TMPDIR=`mktemp -d -p /mnt/crashanalysis/crash_analysis/tmp`

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

techo "Processing for DATE: $DATE and WEEK: $WEEK"

techo "Phase 1: start"
for I in Firefox Thunderbird SeaMonkey
do
  techo "Phase 1: Product: $I"
  techo "Running psql query for version list."
  VERSIONS=`psql -t -U $SECRETS_POSTGRESQL_DATABASE_USERNAME -h $RESOURCE_POSTGRESQL_DATABASE_HOSTNAME breakpad -c "select version, count(*) as counts from reports_${WEEK}  where completed_datetime < $SQL_DATE and completed_datetime > ($SQL_DATE - interval '24 hours') and product = '${I}' group by version order by counts desc limit 3" | awk '{print $1}'`
  for J in $VERSIONS
  do
    techo "Phase 1: Version: $J start"
    techo "Pulling processed JSON from PostgreSQL"
    psql -t -U $SECRETS_POSTGRESQL_DATABASE_USERNAME -h $RESOURCE_POSTGRESQL_DATABASE_HOSTNAME breakpad -c "copy (select processed_crashes.uuid, processed_crash from processed_crashes join reports_${WEEK} on (reports_${WEEK}.uuid::uuid = processed_crashes.uuid) where completed_datetime < $SQL_DATE and completed_datetime > ($SQL_DATE - interval '24 hours') and product = '${I}' and version = '${J}') to stdout with csv quote e'\x01' delimiter e'\x02'" | /data/bin/tar_crashes.py $TMPDIR/${I}_${J}.tar
    techo "per-crash-core-count.py > $TMPDIR/${DATE}_${I}_${J}-core-counts.txt"
    $PYTHON /data/crash-data-tools/per-crash-core-count.py -p ${I} -r ${J} -f $TMPDIR/${I}_${J}.tar > $TMPDIR/${DATE}_${I}_${J}-core-counts.txt
    techo "per-crash-interesting-modules.py > $TMPDIR/${DATE}_${I}_${J}-interesting-modules.txt"
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -p ${I} -r ${J} -f $TMPDIR/${I}_${J}.tar > $TMPDIR/${DATE}_${I}_${J}-interesting-modules.txt
    techo "per-crash-interesting-modules.py > $TMPDIR/${DATE}_${I}_${J}-interesting-modules-with-versions.txt"
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -v -p ${I} -r ${J} -f $TMPDIR/${I}_${J}.tar > $TMPDIR/${DATE}_${I}_${J}-interesting-modules-with-versions.txt
    techo "per-crash-interesting-modules.py > $TMPDIR/${DATE}_${I}_${J}-interesting-addons.txt"
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -a -p ${I} -r ${J} -f $TMPDIR/${I}_${J}.tar > $TMPDIR/${DATE}_${I}_${J}-interesting-addons.txt
    techo "per-crash-interesting-modules.py > $TMPDIR/${DATE}_${I}_${J}-interesting-addons-with-versions.txt"
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -v -a -p ${I} -r ${J} -f $TMPDIR/${I}_${J}.tar > $TMPDIR/${DATE}_${I}_${J}-interesting-addons-with-versions.txt
    techo "Phase 1: Version: $J end"
  done
  techo "Phase 1: end"
done

#MANUAL_VERSION_OVERRIDE="47.0b1 47.0b2 47.0b3 47.0b4 47.0b5 47.0b6 47.0b7 47.0b8 47.0b9 47.0b99 48.0a2 49.0a1"
VERSIONS=`./active-firefox-versions.py`
techo "Phase 2: start"
for I in Firefox
do
  techo "Phase 2: Product: $I"
  for J in $VERSIONS
  do
    techo "Phase 1: Version: $J start"
    techo "Pulling processed JSON from PostgreSQL"
    psql -t -U $SECRETS_POSTGRESQL_DATABASE_USERNAME -h $RESOURCE_POSTGRESQL_DATABASE_HOSTNAME breakpad -c "copy (select processed_crashes.uuid, processed_crash from processed_crashes join reports_${WEEK} on (reports_${WEEK}.uuid::uuid = processed_crashes.uuid) where completed_datetime < $SQL_DATE and completed_datetime > ($SQL_DATE - interval '24 hours') and product = '${I}' and version = '${J}') to stdout with csv quote e'\x01' delimiter e'\x02'" | /data/bin/tar_crashes.py $TMPDIR/${I}_${J}.tar
    techo "per-crash-core-count.py > $TMPDIR/${DATE}_${I}_${J}-core-counts.txt"
    $PYTHON /data/crash-data-tools/per-crash-core-count.py -p ${I} -r ${J} -f $TMPDIR/${I}_${J}.tar > $TMPDIR/${DATE}_${I}_${J}-core-counts.txt
    techo "per-crash-interesting-modules.py > $TMPDIR/${DATE}_${I}_${J}-interesting-modules.txt"
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -p ${I} -r ${J} -f $TMPDIR/${I}_${J}.tar > $TMPDIR/${DATE}_${I}_${J}-interesting-modules.txt
    techo "per-crash-interesting-modules.py > $TMPDIR/${DATE}_${I}_${J}-interesting-modules-with-versions.txt"
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -v -p ${I} -r ${J} -f $TMPDIR/${I}_${J}.tar > $TMPDIR/${DATE}_${I}_${J}-interesting-modules-with-versions.txt
    techo "per-crash-interesting-modules.py > $TMPDIR/${DATE}_${I}_${J}-interesting-addons.txt"
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -a -p ${I} -r ${J} -f $TMPDIR/${I}_${J}.tar > $TMPDIR/${DATE}_${I}_${J}-interesting-addons.txt
    techo "per-crash-interesting-modules.py > $TMPDIR/${DATE}_${I}_${J}-interesting-addons-with-versions.txt"
    $PYTHON /data/crash-data-tools/per-crash-interesting-modules.py -v -a -p ${I} -r ${J} -f $TMPDIR/${I}_${J}.tar > $TMPDIR/${DATE}_${I}_${J}-interesting-addons-with-versions.txt
    techo "Phase 2: Version: $J end"
  done
  techo "Phase 2: end"
done

techo "find $TMPDIR -name ${DATE}\* -type f -size +500k | xargs gzip -9"
find $TMPDIR -name ${DATE}\* -type f -size +500k | xargs gzip -9
techo "mkdir /mnt/crashanalysis/crash_analysis/${DATE}"
mkdir /mnt/crashanalysis/crash_analysis/${DATE}
techo "cp $TMPDIR/${DATE}* /mnt/crashanalysis/crash_analysis/${DATE}/"
cp $TMPDIR/${DATE}* /mnt/crashanalysis/crash_analysis/${DATE}/
techo "rm -rf $TMPDIR"
rm -rf $TMPDIR

techo "unlock cron_libraries"
unlock $NAME

techo "exit 0"
exit 0
