#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs tests.
#
# This should be called from inside a container and after the dependent
# services have been launched. It depends on:
#
# * elasticsearch
# * localstack-s3
# * postgresql
# * pubsub

# Failures should cause setup to fail
set -v -e -x

echo ">>> set up environment"
# Set up environment variables

# NOTE(willkg): This has to be "database_url" all lowercase because configman.
DATABASE_URL=${database_url:-"postgres://postgres:aPassword@postgresql:5432/socorro_test"}

# NOTE(willkg): This has to be "elasticsearch_url" all lowercase because configman.
ELASTICSEARCH_URL=${elasticsearch_url:-"http://elasticsearch:9200"}

export PYTHONPATH=/app/:$PYTHONPATH
PYTEST="$(which pytest)"
PYTHON="$(which python)"

echo ">>> wait for services"
# Wait for postgres and elasticsearch services to be ready
urlwait "${DATABASE_URL}" 10
urlwait "http://${PUBSUB_EMULATOR_HOST}" 10
urlwait "${ELASTICSEARCH_URL}" 10
urlwait "${CRASHSTORAGE_ENDPOINT_URL}" 10

echo ">>> build pubsub things and db things"
# Clear Pub/Sub for tests
./socorro-cmd pubsub delete
./socorro-cmd pubsub create

# Set up socorro_test db
./socorro-cmd db drop || true
./socorro-cmd db create
pushd webapp-django
${PYTHON} manage.py migrate
popd

# Run tests
"${PYTEST}"

# Collect static and then run py.test in the webapp
pushd webapp-django
${PYTHON} manage.py collectstatic --noinput
"${PYTEST}"
