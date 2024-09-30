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
LEGACY_ELASTICSEARCH_URL="${LEGACY_ELASTICSEARCH_URL:-}"

export PYTHONPATH=/app/:$PYTHONPATH
PYTEST="$(which pytest)"
PYTHON="$(which python)"

echo ">>> wait for services to be ready"

urlwait "${DATABASE_URL}"
urlwait "${LEGACY_ELASTICSEARCH_URL}"
urlwait "http://${PUBSUB_EMULATOR_HOST}" 10
urlwait "${STORAGE_EMULATOR_HOST}/storage/v1/b" 10
python ./bin/waitfor.py --verbose --codes=200,404 "${SENTRY_DSN}"
# wait for this last because it's slow to start
urlwait "${ELASTICSEARCH_URL}" 30

echo ">>> build queue things and db things"

# Clear Pub/Sub for tests
./socorro-cmd pubsub delete-all

# Set up socorro_test db
./socorro-cmd db drop || true
./socorro-cmd db create
pushd webapp
${PYTHON} manage.py migrate
popd


echo ">>> run tests"

# Run socorro tests
# ignore tests because elasticsearch 8 tests cannot be run with LEGACY_ONLY
ELASTICSEARCH_MODE=LEGACY_ONLY "${PYTEST}" --ignore=socorro/tests/external/es/
# ignore tests because elasticsearch 8 supersearch is not implemented yet
ELASTICSEARCH_MODE=PREFER_NEW "${PYTEST}"

# Collect static and then run pytest in the webapp
pushd webapp
${PYTHON} manage.py collectstatic --noinput
ELASTICSEARCH_MODE=LEGACY_ONLY "${PYTEST}"
ELASTICSEARCH_MODE=PREFER_NEW "${PYTEST}"
popd
