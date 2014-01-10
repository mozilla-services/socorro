#!/bin/bash

# elasticsearch integration test for Socorro

if [ -z "$ES_HOST" ]
then
  ES_HOST="localhost"
fi

echo -n "INFO: setting up environment..."
make bootstrap > setup.log 2>&1
if [ $? != 0 ]
then
  fatal 1 "could not set up virtualenv"
fi
. socorro-virtualenv/bin/activate >> setup.log 2>&1
if [ $? != 0 ]
then
  fatal 1 "could not activate virtualenv"
fi
export PYTHONPATH=.
echo " Done."

echo -n "INFO: running elasticsearch integration"
python socorro/integrationtest/test_elasticsearch_storage_app.py --elasticsearch_urls="http://${ES_HOST}:9200" --elasticsearch_index=socorro_integration_test --elasticsearch_emails_index=socorro_integration_test
