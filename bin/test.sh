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

./bin/waitfor_services.sh

echo ">>> build queue things and db things"

# Clear Pub/Sub for tests
pubsub-cli delete-topic "$PUBSUB_PROJECT_ID" "$PUBSUB_STANDARD_TOPIC_NAME"
pubsub-cli delete-topic "$PUBSUB_PROJECT_ID" "$PUBSUB_PRIORITY_TOPIC_NAME"
pubsub-cli delete-topic "$PUBSUB_PROJECT_ID" "$PUBSUB_REPROCESSING_TOPIC_NAME"

# Set up socorro_test db
./socorro-cmd db drop || true
./socorro-cmd db create
pushd webapp
${PYTHON} manage.py migrate
popd


echo ">>> run tests"

# Run socorro tests
ELASTICSEARCH_MODE=PREFER_NEW "${PYTEST}"

# Collect static and then run pytest in the webapp
pushd webapp
${PYTHON} manage.py collectstatic --noinput
ELASTICSEARCH_MODE=PREFER_NEW "${PYTEST}"
popd
