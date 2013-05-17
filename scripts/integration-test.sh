#!/bin/bash

# integration test for Socorro
#
# bring up components, submit test crash, ensure that it shows up in
# reports tables.
#
# This uses the same setup as http://socorro.readthedocs.org/en/latest/installation.html

if [ "$#" != "1" ] || [ "$1" != "--destroy" ]
then
  echo "WARNING - this script will destroy the local socorro install."
  echo "The default database and config files will be overwritten."
  echo "You must pass the --destroy flag to continue."
  exit 1
fi

if [ -z "$DB_HOST" ]
then
  DB_HOST="localhost"
fi

if [ -z "$DB_USER" ]
then
  DB_USER="breakpad_rw"
fi

if [ -z "$DB_PASSWORD" ]
then
  DB_PASSWORD="aPassword"
fi

function cleanup() {
  echo "INFO: cleaning up crash storage directories"
  rm -rf ./primaryCrashStore/ ./processedCrashStore/

  echo "INFO: Terminating background jobs"

  for p in collector processor monitor middleware
  do
    # destroy any running processes started by this shell
    kill `jobs -p`
    # destroy anything trying to write to the log files too
    fuser -k ${p}.log > /dev/null 2>&1
  done

  return 0
}

trap 'cleanup' INT

function fatal() {
  exit_code=$1
  message=$2

  echo "ERROR: $message"

  cleanup

  exit $exit_code
}

echo -n "INFO: setting up environment..."
make virtualenv > setup.log 2>&1
if [ $? != 0 ]
then
  fatal 1 "could not set up virtualenv"
fi
. socorro-virtualenv/bin/activate >> setup.log 2>&1
if [ $? != 0 ]
then
  fatal 1 "could activate virtualenv"
fi
export PYTHONPATH=.
echo " Done."

echo -n "INFO: setting up database..."
python socorro/external/postgresql/setupdb_app.py --database_username=$DB_USER --database_password=$DB_PASSWORD --database_name=breakpad --database_hostname=$DB_HOST --dropdb --force --fakedata --fakedata_days=1 > setupdb.log 2>&1
if [ $? != 0 ]
then
  fatal 1 "setupdb_app.py failed, check setupdb.log"
fi
popd >> setupdb.log 2>&1
python socorro/cron/crontabber.py --database.database_host=$DB_HOST --database.database_user=$DB_USER --database.database_password=$DB_PASSWORD --job=weekly-reports-partitions --force >> setupdb.log 2>&1
if [ $? != 0 ]
then
  fatal 1 "crontabber weekly-reports-partitions failed, check setupdb.log"
fi
echo " Done."

echo -n "INFO: configuring backend jobs..."
for p in collector processor middleware crashmover
do
  cp config/${p}.ini-dist config/${p}.ini
  if [ $? != 0 ]
  then
    fatal 1 "copying default config for $p failed"
  fi
  # ensure no running processes
  fuser -k ${p}.log > /dev/null 2>&1
done
echo " Done."

echo -n "INFO: starting up collector, processor, monitor and middleware..."
python socorro/collector/collector_app.py --admin.conf=./config/collector.ini > collector.log 2>&1 &
python socorro/collector/crashmover_app.py --admin.conf=./config/crashmover.ini > crashmover.log 2>&1 &
python socorro/processor/processor_app.py --admin.conf=./config/processor.ini > processor.log 2>&1 &
sleep 1
python socorro/middleware/middleware_app.py --admin.conf=./config/middleware.ini --database.database_host=$DB_HOST > middleware.log 2>&1 &
echo " Done."

function retry() {
  name=$1
  search=$2

  count=0
  while true
  do
    grep "$search" ${name}.log > /dev/null
    if [ $? != 0 ]
    then
      echo "INFO: waiting for $name..."
      if [ $count == 30 ]
      then
        fatal 1 "$name timeout"
      fi
    else
      grep 'ERROR' ${name}.log
      if [ $? != 1 ]
      then
        fatal 1 "errors found in $name.log"
      fi
      echo "INFO: $name test passed"
      break
    fi
    sleep 5
    count=$((count+1))
  done
  }

# wait for collector to startup
retry 'collector' 'running standalone at 127.0.0.1:8882'

echo -n 'INFO: submitting test crash...'
# submit test crash
python socorro/collector/submitter_app.py -u http://localhost:8882/submit -s testcrash/ -n 1 > submitter.log 2>&1
if [ $? != 0 ]
then
  fatal 1 "submitter failed, check submitter.log"
fi
echo " Done."

CRASHID=`grep 'CrashID' submitter.log | awk -FCrashID=bp- '{print $2}'`
if [ -z "$CRASHID" ]
then
  fatal 1 "no crash ID found in submitter log"
fi

echo "INFO: collector received crash ID: $CRASHID"

# make sure crashes are picked up, and no errors are logged
retry 'collector' "$CRASHID"
retry 'processor' "$CRASHID"

# check that mware has raw crash
curl -s -D middleware_headers.log "http://localhost:8883/crash_data/datatype/raw/uuid/${CRASHID}" > /dev/null
if [ $? != 0 ]
then
  fatal 1 "curl call to middleware for raw crash failed"
fi
grep '200 OK' middleware_headers.log > /dev/null
if [ $? != 0 ]
then
  fatal 1 "middleware test failed, no raw data for crash ID $CRASHID"
fi

# check that mware has processed crash in postgres
count=0
while true
do
  curl -s "http://localhost:8883/crash/uuid/${CRASHID}"  | grep '"total": 1' > /dev/null
  if [ $? != 0 ]
  then
    echo "INFO: waiting for middleware..."
    if [ $count == 30 ]
    then
      fatal 1 "middleware test failed, crash ID $CRASHID not found"
    fi
  else
    break
  fi
  sleep 5
  count=$((count+1))
done

# check that mware logs the request for the crash, and logs no errors
retry 'middleware' "$CRASHID"

cleanup
