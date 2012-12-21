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

function cleanup() {
  echo "INFO: Terminating background jobs"
  
  for p in collector processor monitor
  do
    # destroy any running processes started by this shell
    kill `jobs -p`
    # destroy anything trying to write to the log files too
    fuser -k ${p}.log > /dev/null 2>&1
  done
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
. socorro-virtualenv/bin/activate >> setup.log 2>&1
export PYTHONPATH=.
echo " Done."

echo -n "INFO: setting up database..."
python socorro/external/postgresql/setupdb_app.py --database_name=breakpad --dropdb --force > setupdb.log 2>&1
pushd tools/dataload >> setupdb.log 2>&1
bash import.sh >> setupdb.log 2>&1
popd >> setupdb.log 2>&1
python socorro/cron/crontabber.py  --job=weekly-reports-partitions --force >> setupdb.log 2>&1
echo " Done."

echo -n "INFO: copying default config..."
cp config/collector.ini-dist config/collector.ini
cp config/processor.ini-dist config/processor.ini
cp config/monitor.ini-dist config/monitor.ini
cp config/middleware.ini-dist config/middleware.ini
echo " Done."

echo -n "INFO: starting up collector, processor, monitor and middleware..."
for p in collector processor monitor middleware
do
  # ensure no running processes
  fuser -k ${p}.log > /dev/null 2>&1
  python socorro/${p}/${p}_app.py --admin.conf=./config/${p}.ini > ${p}.log 2>&1 &
  sleep 1
done
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
      if [ $count == 10 ]
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
    sleep 1
    count=$((count+1))
  done
  }

# wait for collector to startup
retry 'collector' 'running standalone at 127.0.0.1:8882'

echo -n 'INFO: submitting test crash...'
# submit test crash
python socorro/collector/submitter_app.py -u http://localhost:8882/submit -s testcrash/ > submitter.log 2>&1
echo " Done."

CRASHID=`grep 'CrashID' submitter.log | awk -FCrashID=bp- '{print $2}'`
if [ -z "$CRASHID" ]
then
  fatal 1 "no crash ID found in submitter log"
fi

echo "INFO: collector received crash ID: $CRASHID"

# make sure crashes are picked up, and no errors are logged
retry 'collector' "$CRASHID"
retry 'monitor' "$CRASHID"
retry 'processor' "$CRASHID"

# check that mware has raw crash
curl -s "http://localhost:8883/crash/uuid/${CRASHID}"  | grep '"total": 1"' > /dev/null
if [ $? != 0 ]
then
  fatal 1 "middleware test failed, crash ID $CRASHID not found"
else
  echo "INFO: middleware passed"
fi

# check that mware logs the request for the crash, and logs no errors
retry 'processor' "$CRASHID"

cleanup
