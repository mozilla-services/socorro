#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/test.sh
#
# Runs tests.
#
# Note: This should be called from inside a container.

set -euxo pipefail

echo ">>> set up environment"

# Set up environment variables

DATABASE_URL="${DATABASE_URL:-}"
SENTRY_DSN="${SENTRY_DSN:-}"
ELASTICSEARCH_URL="${ELASTICSEARCH_URL:-}"
LOCAL_DEV_AWS_ENDPOINT_URL="${LOCAL_DEV_AWS_ENDPOINT_URL:-}"

export PYTHONPATH=/app/:$PYTHONPATH
PYTEST="$(which pytest)"
PYTHON="$(which python)"

echo ">>> wait for services to be ready"

urlwait "${DATABASE_URL}"
urlwait "${ELASTICSEARCH_URL}"
urlwait "http://${PUBSUB_EMULATOR_HOST}" 10
urlwait "${STORAGE_EMULATOR_HOST}/storage/v1/b" 10
python ./bin/waitfor.py --verbose --codes=200,404 "${SENTRY_DSN}"
python ./bin/waitfor.py --verbose "${LOCAL_DEV_AWS_ENDPOINT_URL}health"

echo ">>> build sqs things and db things"

# Clear SQS for tests
./socorro-cmd sqs delete-all

# Set up socorro_test db
./socorro-cmd db drop || true
./socorro-cmd db create
pushd webapp
${PYTHON} manage.py migrate
popd


echo ">>> run tests"

# Run socorro tests
"${PYTEST}"

# Collect static and then run pytest in the webapp
pushd webapp
${PYTHON} manage.py collectstatic --noinput
"${PYTEST}"
popd
