#!/bin/bash

# integration test for Socorro, using rabbitmq
#
# bring up components, submit test crash, ensure that it shows up in
# reports tables.
#
# This uses the same setup as http://socorro.readthedocs.org/en/latest/installation.html

echo "this is integration-test.sh"

export PATH=$PATH:${VIRTUAL_ENV:-"socorro-virtualenv"}/bin:$PWD/scripts
export PYTHONPATH=.

source scripts/defaults

if [ "$#" != "1" ] || [ "$1" != "--destroy" ]
then
  echo "WARNING - this script will destroy the local socorro install."
  echo "The default database and config files will be overwritten."
  echo "You must pass the --destroy flag to continue."
  exit 1
fi

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#  support functions section
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

#------------------------------------------------------------------------------
# send in an error code and a message.
# If the error is 0, do nothing
# If the error is anything else, send the message to stdout and then
# exit using the error code
#------------------------------------------------------------------------------
function fatal() {
  exit_code=$1
  message=$2

  if [ $exit_code != 0 ]
  then
    echo "ERROR: $message"
    cleanup
    exit $exit_code
  fi
}

#------------------------------------------------------------------------------
# send in an error code, the basename of a log file, and a message
# if the error code is 0, do nothing
# if the error code is anything else, send the message to stdout, cat the log
# file associated with the basename, then send the error code on to the 'fatal'
# function
#------------------------------------------------------------------------------
function cat_log_on_error() {
  error_code=$1
  log_base_name=$2
  message=$3
  if [ $error_code != 0 ]
  then
    echo "$log_base_name failed, $message"
    cat $log_base_name.log
    fatal $error_code "$log_base_name failure terminated this test with error code $error_code"
  fi
}

#------------------------------------------------------------------------------
# send in the basename of a log file
# if the words ERROR or CRIT are in the log file, send a message about it to
# stdout, cat the log file, then pass the error along with a message to the
# 'fatal' function
#------------------------------------------------------------------------------
function cat_log_on_log_error() {
  log_base_name=$1
  for err_type in ERROR CRIT
  do
    grep $err_type $log_base_name.log > /dev/null
    err_found=$?
    if [ $err_found = 0 ]
    then
      echo "$log_base_name.log contanins $err_type"
      cat $log_base_name.log
      fatal $err_found "$log_base_name $err_type terminated this test"
    fi
  done
}

#------------------------------------------------------------------------------
# send in an error code and the base name of a log file.
# offer these to the error code test function 'cat_log_on_log_error' and the
# the log file test function 'cat_log_on_error'
#------------------------------------------------------------------------------
function check_for_logged_fatal_errors() {
  error_code=$1
  log_base_name=$2
  cat_log_on_log_error $log_base_name
  cat_log_on_error $error_code $log_base_name "much to your displeasure"
}

#------------------------------------------------------------------------------
# iterate through the names of the RabbitMQ queues clearing them out using the
# 'test_rabbitmq.py' Socorro app. Send the result to the error reporting
# function 'check_for_logged_fatal_errors'
#------------------------------------------------------------------------------
function cleanup_rabbitmq() {
  for queue_name in $rmq_normal_queue_name $rmq_priority_queue_name $rmq_reprocessing_queue_name
  do
    echo "INFO: Purging rabbitmq queue" $queue_name
    socorro purge_rmq $queue_name \
        --host=$rmq_host \
        --rabbitmq_user=$rmq_user \
        --rabbitmq_password=$rmq_password \
        --virtual_host=$rmq_virtual_host \
        > $queue_name.log 2>&1
    check_for_logged_fatal_errors $? $queue_name
  done
}

#------------------------------------------------------------------------------
# empty the rabbit queues, clean the local filesystem, kill any apps that this
# shell script may have started
#------------------------------------------------------------------------------
function cleanup() {
  cleanup_rabbitmq

  echo "INFO: cleaning up crash storage directories"
  rm -rf ./primaryCrashStore/ ./processedCrashStore/
  rm -rf ./crashes/
  rm -rf ./submissions
  rm -rf ./correlations

  echo "INFO: Terminating background jobs"
  echo "  any kill usage errors below may be ignored"

  for p in collector processor middleware
  do
    # destroy any running processes started by this shell
    kill $(jobs -p) > /dev/null 2>&1
    # destroy anything trying to write to the log files too
    fuser -k ${p}.log > /dev/null 2>&1
  done

}
# associate this function with the signals so that on receipt of one of these
# symbols, the 'cleanup' function is invoked
trap 'cleanup' SIGINT SIGTERM SIGHUP

#------------------------------------------------------------------------------
# send in a basename of log file and a command to run
# repeatedly run the command until it has been run 10 times or the command
# succeeds.  If it times out, cat the associated log file.  if the command
# succeeds, send any error code to the 'cat_log_on_log_error' function
#------------------------------------------------------------------------------
function retry_command() {
  name=$1
  command_str=$2
  count=0
  while true
  do
    $command_str >/dev/null
    if [ $? != 0 ]
    then
      echo "INFO: waiting for $name..."
      if [ $count == 30 ]
      then
        cat $name.log
        fatal 1 "$name timeout"
      fi
      sleep 5
      count=$((count+1))
    else
      cat_log_on_log_error $name
      echo "INFO: $name app is without errors"
      break
    fi
  done
}

#------------------------------------------------------------------------------
# send in a basename of a log file and a search term.
# grep for the search term in the log file.
#------------------------------------------------------------------------------
function retry() {
  name=$1
  search=$2
  count=0
  while true
  do
    grep -q "$search" $name.log
    if [ $? != 0 ]
    then
      echo "INFO: waiting for $name..."
      if [ $count == 10 ]
      then
        cat $name.log
        fatal 1 "$name timeout"
      fi
      # we're waiting for a process to finish a task that might take some time
      sleep 5
      count=$((count+1))
    else
      cat_log_on_log_error $name
      echo "INFO: $name app is without errors"
      break
    fi
  done
}

#------------------------------------------------------------------------------
# setup and run the collector, processor and middleware
# The collector should be configured using the 2015 method of having the
# ability to collect multiple crash types using different end points.
#    breakpad crashes on /submit
#    pellet stove data on /pellet/submit
#----------------------------------------------------------------------------
function start_2015_socorro_apps() {
  echo "INFO: starting up *** start_2015_socorro_apps *** "
  echo "      * in this test we're using a collector2015 capable of accepting 2 types of crashes"
  echo "      * the collector writes to both the filesystem using FSPermanentStorage & to RabbitMQ using the $rmq_normal_queue_name queue"
  echo "      * the processor used Processor2015 with the MozillaProcessorAlgorithm2015"
  socorro collector2015 \
      --services.services_controller='[{"name": "collector", "uri": "/submit", "service_implementation_class": "socorro.collector.wsgi_breakpad_collector.BreakpadCollector2015"}, {"name": "pellet_stove", "uri": "/pellet/submit", "service_implementation_class": "socorro.collector.wsgi_generic_collector.GenericCollector"}]' \
      --services.collector.storage.crashstorage_class=socorro.external.crashstorage_base.PolyCrashStorage \
      --services.collector.storage.storage_classes='socorro.external.fs.crashstorage.FSPermanentStorage, socorro.external.rabbitmq.crashstorage.RabbitMQCrashStorage' \
      --services.collector.storage.storage0.crashstorage_class=socorro.external.fs.crashstorage.FSPermanentStorage \
      --services.collector.storage.storage1.crashstorage_class=socorro.external.rabbitmq.crashstorage.RabbitMQCrashStorage \
      --services.pellet_stove.storage.crashstorage_class=socorro.external.fs.crashstorage.FSPermanentStorage \
      --services.pellet_stove.storage.fs_root=./submissions \
      --resource.rabbitmq.host=$rmq_host \
      --secrets.rabbitmq.rabbitmq_user=$rmq_user \
      --secrets.rabbitmq.rabbitmq_password=$rmq_password \
      --resource.rabbitmq.virtual_host=$rmq_virtual_host \
      --resource.rabbitmq.standard_queue_name=$rmq_normal_queue_name \
      --resource.rabbitmq.priority_queue_name=$rmq_priority_queue_name \
      --resource.rabbitmq.reprocessing_queue_name=$rmq_reprocessing_queue_name \
      --resource.rabbitmq.routing_key=$rmq_normal_queue_name \
      --resource.rabbitmq.transaction_executor_class=socorro.database.transaction_executor.TransactionExecutor \
      --web_server.wsgi_server_class=socorro.webapi.servers.CherryPy \
      --web_server.ip_address=0.0.0.0 \
      > collector.log 2>&1 &
  echo '   collector started'
  socorro processor \
      --resource.rabbitmq.host=$rmq_host \
      --secrets.rabbitmq.rabbitmq_user=$rmq_user \
      --secrets.rabbitmq.rabbitmq_password=$rmq_password \
      --resource.rabbitmq.virtual_host=$rmq_virtual_host \
      --resource.rabbitmq.standard_queue_name=$rmq_normal_queue_name \
      --resource.rabbitmq.priority_queue_name=$rmq_priority_queue_name \
      --resource.rabbitmq.reprocessing_queue_name=$rmq_reprocessing_queue_name \
      --resource.rabbitmq.routing_key=$rmq_normal_queue_name \
      --resource.postgresql.database_hostname=$database_hostname \
      --secrets.postgresql.database_username=$database_username \
      --secrets.postgresql.database_password=$database_password \
      --new_crash_source.new_crash_source_class=socorro.external.rabbitmq.rmq_new_crash_source.RMQNewCrashSource \
      --processor.processor_class=socorro.processor.mozilla_processor_2015.MozillaProcessorAlgorithm2015 \
      > processor.log 2>&1 &
  echo '   processor started'

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
      --rabbitmq.standard_queue_name=$rmq_normal_queue_name \
      --rabbitmq.priority_queue_name=$rmq_priority_queue_name \
      --rabbitmq.reprocessing_queue_name=$rmq_reprocessing_queue_name \
      --web_server.wsgi_server_class=socorro.webapi.servers.CherryPy \
      > middleware.log 2>&1 &
  echo '   middleware started'

  # tell the test routine to use the extra submission test
  extra_submission_test=1
  echo " Done."
}

#------------------------------------------------------------------------------
# setup and run the collector, processor and middleware
# The collector will use the traditional wsgi function that can only receive
# breakpad crashes on the endpoint /submit
#------------------------------------------------------------------------------
function start_standard_socorro_apps() {
  echo "INFO: starting up *** start_standard_socorro_apps *** "
  echo "      * in this test we're using the older collector capable of accepting only breakpad crashes"
  echo "      * the collector writes to both the filesystem using FSPermanentStorage & to RabbitMQ using the $rmq_normal_queue_name queue"
  echo "      * the processor used Processor2015 with the MozillaProcessorAlgorithm2015"
  socorro collector \
      --storage.crashstorage_class=socorro.external.crashstorage_base.PolyCrashStorage \
      --storage.storage_classes='socorro.external.fs.crashstorage.FSPermanentStorage, socorro.external.rabbitmq.crashstorage.RabbitMQCrashStorage' \
      --storage.storage0.crashstorage_class=socorro.external.fs.crashstorage.FSPermanentStorage \
      --storage.storage1.crashstorage_class=socorro.external.rabbitmq.crashstorage.RabbitMQCrashStorage \
      --resource.rabbitmq.host=$rmq_host \
      --secrets.rabbitmq.rabbitmq_user=$rmq_user \
      --secrets.rabbitmq.rabbitmq_password=$rmq_password \
      --resource.rabbitmq.virtual_host=$rmq_virtual_host \
      --resource.rabbitmq.standard_queue_name=$rmq_normal_queue_name \
      --resource.rabbitmq.priority_queue_name=$rmq_priority_queue_name \
      --resource.rabbitmq.reprocessing_queue_name=$rmq_reprocessing_queue_name \
      --resource.rabbitmq.routing_key=$rmq_normal_queue_name \
      --resource.rabbitmq.transaction_executor_class=socorro.database.transaction_executor.TransactionExecutor \
      --web_server.wsgi_server_class=socorro.webapi.servers.CherryPy \
      --web_server.ip_address=0.0.0.0 \
      > collector.log 2>&1 &
  socorro processor \
      --resource.rabbitmq.host=$rmq_host \
      --secrets.rabbitmq.rabbitmq_user=$rmq_user \
      --secrets.rabbitmq.rabbitmq_password=$rmq_password \
      --resource.rabbitmq.virtual_host=$rmq_virtual_host \
      --resource.rabbitmq.standard_queue_name=$rmq_normal_queue_name \
      --resource.rabbitmq.priority_queue_name=$rmq_priority_queue_name \
      --resource.rabbitmq.reprocessing_queue_name=$rmq_reprocessing_queue_name \
      --resource.rabbitmq.routing_key=$rmq_normal_queue_name \
      --resource.postgresql.database_hostname=$database_hostname \
      --secrets.postgresql.database_username=$database_username \
      --secrets.postgresql.database_password=$database_password \
      --new_crash_source.new_crash_source_class=socorro.external.rabbitmq.rmq_new_crash_source.RMQNewCrashSource \
      --processor.processor_class=socorro.processor.mozilla_processor_2015.MozillaProcessorAlgorithm2015 \
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
      --rabbitmq.standard_queue_name=$rmq_normal_queue_name \
      --rabbitmq.priority_queue_name=$rmq_priority_queue_name \
      --rabbitmq.reprocessing_queue_name=$rmq_reprocessing_queue_name \
      --web_server.wsgi_server_class=socorro.webapi.servers.CherryPy \
      > middleware.log 2>&1 &

  # tell the test routine NOT to use the extra submission test
  extra_submission_test=0

  echo " Done."
}

#------------------------------------------------------------------------------
# setup and run the collector, processor and middleware WITHOUT RabbitMQ
# The collector will use the traditional wsgi function that can only receive
# breakpad crashes on the endpoint /submit
# The collector saves in
#------------------------------------------------------------------------------
function start_minimal_socorro_apps() {
  echo "INFO: starting up *** start_minimal_socorro_apps *** "
  echo "      * in this test we're using the older collector capable of accepting only breakpad crashes"
  echo "      * the collector writes to only the filesystem using FSTemporaryStorage"
  echo "      * the processor used Processor2015 with the SocorroLiteProcessorAlgorithm2015"
  echo "      * the processor sources from FSTemporaryStorage"
  echo "      * the processor writes only to FSPermanentStorage"
  socorro collector \
      --storage.crashstorage_class=socorro.external.fs.crashstorage.FSTemporaryStorage \
      --web_server.wsgi_server_class=socorro.webapi.servers.CherryPy \
      --web_server.ip_address=0.0.0.0 \
      > collector.log 2>&1 &
  socorro processor \
      --source.crashstorage_class=socorro.external.fs.crashstorage.FSTemporaryStorage \
      --new_crash_source.new_crash_source_class=socorro.external.fs.fs_new_crash_source.FSNewCrashSource \
      --new_crash_source.crashstorage_class=socorro.external.fs.crashstorage.FSTemporaryStorage \
      --processor.processor_class=socorro.processor.socorrolite_processor_2015.SocorroLiteProcessorAlgorithm2015 \
      --destination.crashstorage_class=socorro.external.fs.crashstorage.FSPermanentStorage \
      --destination.fs_root=./processedCrashStore \
      > processor.log 2>&1 &
  sleep 1
  socorro middleware \
      --admin.conf=./config/middleware.ini \
      --database.database_hostname=$database_hostname \
      --database.database_username=$database_username \
      --database.database_password=$database_password \
      --filesystem.fs_root=./processedCrashStore \
      --rabbitmq.host=$rmq_host \
      --rabbitmq.rabbitmq_user=$rmq_user \
      --rabbitmq.rabbitmq_password=$rmq_password \
      --rabbitmq.virtual_host=$rmq_virtual_host \
      --rabbitmq.standard_queue_name=$rmq_normal_queue_name \
      --rabbitmq.priority_queue_name=$rmq_priority_queue_name \
      --rabbitmq.reprocessing_queue_name=$rmq_reprocessing_queue_name \
      --web_server.wsgi_server_class=socorro.webapi.servers.CherryPy \
      > middleware.log 2>&1 &
  # tell the test routine NOT to use the extra submission test
  extra_submission_test=0

  echo " Done."
}


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#  integration test section
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

echo "INFO: setting up environment..."
source ${VIRTUAL_ENV:-"socorro-virtualenv"}/bin/activate >> setup.log 2>&1
fatal $? "couldn't activate virtualenv"
echo " Done."

#------------------------------------------------------------------------------
echo "INFO: setting up database..."
socorro setupdb --dropdb --force --createdb > setupdb.log 2>&1
check_for_logged_fatal_errors $? setupdb
echo " Done."
popd >> setupdb.log 2>&1

#------------------------------------------------------------------------------
echo "INFO: setting up 'weekly-reports-partitions' via crontabber..."
python socorro/cron/crontabber_app.py \
    --job=weekly-reports-partitions \
    --force \
    > crontabber_app.log 2>&1
check_for_logged_fatal_errors $? crontabber_app
echo " Done."


#------------------------------------------------------------------------------
echo "INFO: ensure no processes already running..."
cleanup
echo " Done."

#******************************************************************************
# Here's where we actually start testing
# Iterate through some combinations of collector/crashmover/processor/middleware/setups
# These setups are defined in functions with their names list in the for loop:
for an_app_set in start_2015_socorro_apps start_standard_socorro_apps start_minimal_socorro_apps
do
  # start the apps by invoking their function
  $an_app_set

  # wait for collector to startup
  retry collector "running standalone at 0.0.0.0:8882"

  #----------------------------------------------------------------------------
  # BREAKPAD submission test
  echo 'INFO: submitting breakpad test crash...'
  # submit test crash
  socorro submitter \
      -u http://0.0.0.0:8882/submit \
      -s testcrash/raw/ \
      -n 1 \
      > submitter.log 2>&1
  check_for_logged_fatal_errors $? submitter


  CRASHID=$(grep 'CrashID' submitter.log | awk -FCrashID=bp- '{print $2}')
  echo found $CRASHID
  if [ -z "$CRASHID" ]
  then
    echo "ERROR: CRASHID missing from submitter.log"
    echo "***** BEGIN collector log *****"
    cat collector.log
    echo "***** END collector log *****"
    echo "***** BEGIN submitter log *****"
    cat submitter.log
    echo "***** END submitter log *****"
    fatal 1 "no crash ID found in submitter log"
  fi
  echo "INFO: collector received crash ID: $CRASHID"
  echo " Done."

  #----------------------------------------------------------------------------
  # make sure crashes are picked up, and no errors are logged
  retry 'collector' "$CRASHID"
  retry 'processor' "saved - $CRASHID"

  #----------------------------------------------------------------------------
  # check that mware has raw crash using curl to hit the HTTP endpoint
  curl -s -D middleware_headers.log "http://localhost:8883/crash_data/?datatype=meta&uuid=$CRASHID" > /dev/null
  err=$?
  echo "  looking for errors in hitting the middleware for $CRASHID"
  check_for_logged_fatal_errors $err middleware

  echo "  looking for "200 OK" in hitting the middleware for $CRASHID"
  grep '200 OK' middleware_headers.log > /dev/null
  fatal $? "middleware test failed, no raw data for crash ID $CRASHID"

  echo "  looking for processed crash through middleware for $CRASHID"
  function find_crash_in_middleware() {
    curl -s "http://localhost:8883/crash_data/?datatype=processed&uuid=$CRASHID" | grep date_processed
    echo "http://localhost:8883/crash_data/?datatype=processed&uuid=$CRASHID"
    return $?
  }
  retry_command middleware find_crash_in_middleware

  # check that mware logs the request for the crash, and logs no errors
  retry 'middleware' "/crash_data"

  #----------------------------------------------------------------------------
  # EXTRA submission test
  if [ $extra_submission_test = 1 ]
  then
    echo 'INFO: submitting other test crash...'
    # submit test crash
    socorro submitter \
        -u http://0.0.0.0:8882/pellet/submit \
        -s testcrash/not_breakpad/ \
        -n 1 \
        > extra_submitter.log 2>&1

    check_for_logged_fatal_errors  $? extra_submitter
    echo " Done."

    CRASHID_OTHER=$(grep 'CrashID' extra_submitter.log | awk -FCrashID=xx- '{print $2}')
    if [ -z "$CRASHID_OTHER" ]
    then
      echo "ERROR: $CRASHID_OTHER missing from submitter.log"
      echo "***** BEGIN collector log *****"
      cat collector.log
      echo "***** END collector log *****"
      echo "***** BEGIN submitter log *****"
      cat extra_submitter.log
      echo "***** END submitter log *****"
      fatal 1 "no crash ID found in extra_submitter log"
    fi

    echo "INFO: collector received crash ID: $CRASHID_OTHER"

    # make sure crashes are picked up, and no errors are logged
    retry 'collector' "$CRASHID_OTHER"
  fi

  echo "*** $an_app_set *** PASSES INTEGRATION TESTS"
  #----------------------------------------------------------------------------
  cleanup

done

# start correlations integration tests
echo "INFO: starting up *** correlations test *** "
echo "      * in this test, we ensure the correlations reports app produces the correct output in json form"

mkdir ./correlations

socorro correlations \
--source.crashstorage_class=socorro.collector.submitter_app.SubmitterFileSystemWalkerSource \
--source.search_root=testcrash/processed \
--new_crash_source.new_crash_source_class=""  \
--global.correlations.path=./correlations \
--global.correlations.core.output_class=socorro.analysis.correlations.core_count_rule.JsonFileOutputForCoreCounts \
--global.correlations.interesting.output_class=socorro.analysis.correlations.interesting_rule.JsonFileOutputForInterestingModules  \
--producer_consumer.number_of_threads=10 \
--destination.crashstorage_class=socorro.external.crashstorage_base.NullCrashStorage \
--global.correlation.min_count_for_inclusion=1 \
> correlations.log 2>&1

if [ $? = 1 ]
then
    echo "ERROR: correlations logged errors"
    echo "***** BEGIN correlation log *****"
    cat correlations.log
    echo "***** END correlation log *****"
    fatal 1 "ERROR: correlations produced unexpected output"
fi

check_for_logged_fatal_errors $? correlations

diff ./correlations/20151130 ./testcrash/correlations-integration-correct-output >correlation.diff
if [ $? = 1 ]
then
    # something went wrong
    echo "ERROR: correlations produced unexpected output"
    echo "***** BEGIN correlation log *****"
    cat correlations.log
    echo "***** BEGIN correlation diff *****"
    cat correlation.diff
    echo "***** END correlation diff *****"
    fatal 1 "ERROR: correlations produced unexpected output"
fi
echo "*** correlations *** PASSES INTEGRATION TESTS"

echo "If you are reading this, then ALL the integration tests passed!"
exit 0
