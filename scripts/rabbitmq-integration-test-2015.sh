#!/bin/bash

# integration test for Socorro, using rabbitmq
#
# bring up components, submit test crash, ensure that it shows up in
# reports tables.
#
# This uses the same setup as http://socorro.readthedocs.org/en/latest/installation.html

export PATH=$PATH:${VIRTUAL_ENV:-"socorro-virtualenv"}/bin:$PWD/scripts

source scripts/defaults

if [ "$#" != "1" ] || [ "$1" != "--destroy" ]
then
  echo "WARNING - this script will destroy the local socorro install."
  echo "The default database and config files will be overwritten."
  echo "You must pass the --destroy flag to continue."
  exit 1
fi

function cleanup_rabbitmq() {
  echo -n "INFO: Purging rabbitmq queue 'socorro.normal'..."
  python scripts/test_rabbitmq.py --test_rabbitmq.purge='socorro.normal' --test_rabbitmq.rabbitmq_host=$rmq_host --test_rabbitmq.rabbitmq_user=$rmq_user --test_rabbitmq.rabbitmq_password=$rmq_password --test_rabbitmq.rabbitmq_vhost=$rmq_virtual_host > /dev/null 2>&1
  echo " Done."
  echo -n "INFO: Purging rabbitmq queue 'socorro.priority'..."
  python scripts/test_rabbitmq.py --test_rabbitmq.purge='socorro.priority' --test_rabbitmq.rabbitmq_host=$rmq_host --test_rabbitmq.rabbitmq_user=$rmq_user --test_rabbitmq.rabbitmq_password=$rmq_password --test_rabbitmq.rabbitmq_vhost=$rmq_virtual_host > /dev/null 2>&1
  echo " Done."
}

function cleanup() {
  cleanup_rabbitmq

  echo "INFO: cleaning up crash storage directories"
  rm -rf ./primaryCrashStore/ ./processedCrashStore/
  rm -rf ./crashes/
  rm -rf ./submissions

  echo "INFO: Terminating background jobs"

  for p in collector processor middleware
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
  cat setupdb.log

  cleanup

  exit $exit_code
}

echo -n "INFO: setting up environment..."
source ${VIRTUAL_ENV:-"socorro-virtualenv"}/bin/activate >> setup.log 2>&1
if [ $? != 0 ]
then
  fatal 1 "couldn't activate virtualenv"
fi
export PYTHONPATH=.
echo " Done."

echo -n "INFO: setting up database..."
socorro setupdb --dropdb --force --createdb > setupdb.log 2>&1
if [ $? != 0 ]
then
  fatal 1 "setupdb_app.py failed, check setupdb.log"
  cat setupdb.log
fi
echo " Done."
popd >> setupdb.log 2>&1

# ensure rabbitmq is really empty and no previous failure left garbage
cleanup_rabbitmq

echo -n "INFO: setting up 'weekly-reports-partitions' via crontabber..."
python socorro/cron/crontabber_app.py \
    --job=weekly-reports-partitions \
    --force \
    >> setupdb.log 2>&1
if [ $? != 0 ]
then
  fatal 1 "crontabber weekly-reports-partitions failed, check setupdb.log"
fi
echo " Done."

echo -n "INFO: configuring backend jobs..."
for p in collector processor middleware
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

echo -n "INFO: starting up collector, processor and middleware..."
socorro collector2015 \
    --services.services_controller='[{"name": "collector", "uri": "/submit", "service_implementation_class": "socorro.collector.wsgi_breakpad_collector.BreakpadCollector2015"}, {"name": "pellet_stove", "uri": "/pellet/submit", "service_implementation_class": "socorro.collector.wsgi_generic_collector.GenericCollector"}]' \
    --services.collector.storage.crashstorage_class=socorro.external.crashstorage_base.PolyCrashStorage \
    --services.collector.storage.storage_classes='socorro.external.fs.crashstorage.FSPermanentStorage, socorro.external.rabbitmq.crashstorage.RabbitMQCrashStorage' \
    --services.collector.storage.storage0.crashstorage_class=socorro.external.fs.crashstorage.FSPermanentStorage \
    --services.collector.storage.storage1.crashstorage_class=socorro.external.rabbitmq.crashstorage.RabbitMQCrashStorage \
    --services.pellet_stove.storage.crashstorage_class=socorro.external.fs.crashstorage.FSPermanentStorage \
    --services.pellet_stove.storage.fs_root=./submissions \
    --resource.rabbitmq.host=localhost \
    --secrets.rabbitmq.rabbitmq_user=guest \
    --secrets.rabbitmq.rabbitmq_password=guest \
    --resource.rabbitmq.virtual_host=/ \
    --resource.rabbitmq.transaction_executor_class=socorro.database.transaction_executor.TransactionExecutor \
    --web_server.wsgi_server_class=socorro.webapi.servers.CherryPy \
    --web_server.ip_address=0.0.0.0 \
    > collector.log 2>&1 &
socorro processor \
    --admin.conf=./config/processor.ini \
    --resource.rabbitmq.host=$rmq_host \
    --secrets.rabbitmq.rabbitmq_user=$rmq_user \
    --secrets.rabbitmq.rabbitmq_password=$rmq_password \
    --resource.rabbitmq.virtual_host=$rmq_virtual_host \
    --resource.postgresql.database_hostname=$database_hostname \
    --secrets.postgresql.database_username=$database_username \
    --secrets.postgresql.database_password=$database_password \
    --new_crash_source.new_crash_source_class='socorro.external.rabbitmq.rmq_new_crash_source.RMQNewCrashSource' \
    --processor.processor_class='socorro.processor.mozilla_processor_2015.MozillaProcessorAlgorithm2015' \
    > processor.log 2>&1 &

sleep 1
socorro middleware \
    --admin.conf=./config/middleware.ini \
    --database.database_hostname=$database_hostname \
    --database.database_username=$database_username \
    --database.database_password=$database_password \
    --rabbitmq.host=$rmq_host \
    --rabbitmq.rabbitmq_user=$rmq_user \
    --rabbitmq.rabbitmq_password=$rmq_password \
    --rabbitmq.virtual_host=$rmq_virtual_host \
    --web_server.wsgi_server_class=socorro.webapi.servers.CherryPy \
    > middleware.log 2>&1 &
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
        cat $name.log
        fatal 1 "$name timeout"
      fi
    else
      grep 'ERROR' ${name}.log
      if [ $? != 1 ]
      then
        cat ${name}.log
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
retry 'collector' 'running standalone at 0.0.0.0:8882'

# BREAKPAD submission test
echo -n 'INFO: submitting breakpad test crash...'
# submit test crash
socorro submitter \
    -u http://0.0.0.0:8882/submit \
    -s testcrash/raw/ \
    -n 1 \
    > submitter.log 2>&1
if [ $? != 0 ]
then
  fatal 1 "submitter failed, check submitter.log"
fi
echo " Done."

CRASHID=`grep 'CrashID' submitter.log | awk -FCrashID=bp- '{print $2}'`
if [ -z "$CRASHID" ]
then
  cat submitter.log
  fatal 1 "no crash ID found in submitter log"
fi

echo "INFO: collector received crash ID: $CRASHID"

# make sure crashes are picked up, and no errors are logged
retry 'collector' "$CRASHID"
retry 'processor' "$CRASHID"

# OTHER submission test
echo -n 'INFO: submitting other test crash...'
# submit test crash
socorro submitter \
    -u http://0.0.0.0:8882/pellet/submit \
    -s testcrash/not_breakpad/ \
    -n 1 \
    >> submitter.log 2>&1
if [ $? != 0 ]
then
  fatal 1 "submitter failed, check submitter.log"
fi
echo " Done."

CRASHID_OTHER=`grep 'CrashID' submitter.log | awk -FCrashID=xx- '{print $2}'`
if [ -z "$CRASHID_OTHER" ]
then
  cat submitter.log
  fatal 1 "no crash ID found in submitter log"
fi

echo "INFO: collector received crash ID: $CRASHID_OTHER"

# make sure crashes are picked up, and no errors are logged
retry 'collector' "$CRASHID_OTHER"
# no processor for this crash type yet


# check that mware has raw crash
curl -s -D middleware_headers.log "http://localhost:8883/crash_data/?datatype=raw&uuid=${CRASHID}" > /dev/null
if [ $? != 0 ]
then
  echo "***** middleware log *****"
  cat middleware.log
  echo "***** END middleware log *****"
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
  # curl -s "http://localhost:8883/crash_data/?datatype=processed&uuid=${CRASHID}&_force_api_impl=psql"  | grep '"date_processed"' > /dev/null
  curl -s "http://localhost:8883/crash_data/?datatype=processed&uuid=${CRASHID}"  | grep '"date_processed"' > /dev/null
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
retry 'middleware' "/crash_data"

cleanup
