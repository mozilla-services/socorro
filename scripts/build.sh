#!/bin/bash
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Jenkins build script for running tests and packaging build
#
# Inspired by Zamboni
# https://github.com/mozilla/zamboni/blob/master/scripts/build.sh

# any failures in this script should cause the build to fail
set -e

make clean

# copy default unit test configs
pushd socorro/unittest/config
for file in *.py.dist
do
  cp $file `basename $file .dist`
done
popd

errors=0
while read d
do
  if [ ! -f "$d/__init__.py" ]
  then
    echo "$d is missing an __init__.py file, tests will not run"
    errors=$((errors+1))
  fi
done < <(find socorro/unittest/* -not -name logs -type d)

if [ $errors != 0 ]
then
  exit 1
fi

# Override hostnames for jenkins
export DB_HOST="jenkins-pg92"
export RABBITMQ_HOST="rabbitmq-zlb.webapp.phx1.mozilla.com"
export RABBITMQ_USERNAME="socorro-jenkins"
export RABBITMQ_PASSWORD="aPassword"
export RABBITMQ_VHOST="socorro-jenkins"
export ES_HOST="jenkins-es20"

# RHEL postgres 9 RPM installs pg_config here, psycopg2 needs it
export PATH=/usr/pgsql-9.2/bin:$PATH
echo "My path is $PATH"
# run unit tests
make test DB_USER=test DB_HOST=$DB_HOST DB_PASSWORD=aPassword DB_SUPERUSER=test DB_SUPERPASSWORD=aPassword

if [ "$1" != "leeroy" ]
then
  # pull pre-built, known version of breakpad
  make clean
  wget 'https://ci.mozilla.org/job/breakpad/lastSuccessfulBuild/artifact/breakpad.tar.gz'
  tar -zxf breakpad.tar.gz
  mv breakpad stackwalk
fi

# run socorro integration test
echo "Running integration test..."
./scripts/monitor-integration-test.sh --destroy
./scripts/rabbitmq-integration-test.sh --destroy
./scripts/elasticsearch-integration-test.sh

if [ "$1" != "leeroy" ]
then
  # package socorro.tar.gz for distribution
  mkdir builds/
  make install PREFIX=builds/socorro
  make analysis
  tar -C builds --mode 755 --exclude-vcs --owner 0 --group 0 -zcf socorro.tar.gz socorro/
fi
