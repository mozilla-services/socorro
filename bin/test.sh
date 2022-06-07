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

# First convert configman environment vars which have bad identifiers to ones
# that don't
function getenv {
    python -c "import os; print(os.environ['$1'])"
}

DATABASE_URL="${DATABASE_URL:-}"
SENTRY_DSN="${SENTRY_DSN:-}"
ELASTICSEARCH_URL="$(getenv 'resource.elasticsearch.elasticsearch_urls')"
S3_ENDPOINT_URL="$(getenv 'resource.boto.s3_endpoint_url')"
SQS_ENDPOINT_URL="$(getenv 'resource.boto.sqs_endpoint_url')"

export PYTHONPATH=/app/:$PYTHONPATH
PYTEST="$(which pytest)"
PYTHON="$(which python)"

echo ">>> wait for services to be ready"

urlwait "${DATABASE_URL}"
urlwait "${ELASTICSEARCH_URL}"
python ./bin/waitfor.py --verbose --codes=200,404 "${SENTRY_DSN}"
python ./bin/waitfor.py --verbose "${S3_ENDPOINT_URL}health"
python ./bin/waitfor.py --verbose "${SQS_ENDPOINT_URL}health"

echo ">>> build sqs things and db things"

# Clear SQS for tests
./socorro-cmd sqs delete-all

# Set up socorro_test db
./socorro-cmd db drop || true
./socorro-cmd db create
pushd webapp-django
${PYTHON} manage.py migrate
popd


echo ">>> run tests"

# Run socorro tests
"${PYTEST}"

# Collect static and then run pytest in the webapp
pushd webapp-django
${PYTHON} manage.py collectstatic --noinput
"${PYTEST}"
popd
