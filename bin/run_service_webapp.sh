#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/run_service_webapp.sh [--dev]
#
# Runs the webapp service.
#
# Use the "--dev" argument to run the webapp in a docker container for
# local development.
#
# Note: This should be called from inside the socorro_app Docker container.

set -euxo pipefail

PORT=${PORT:-"8000"}
GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-"300"}
GUNICORN_WORKERS=${GUNICORN_WORKERS:-"1"}
GUNICORN_WORKER_CLASS=${GUNICORN_WORKER_CLASS:-"sync"}
GUNICORN_MAX_REQUESTS=${GUNICORN_MAX_REQUESTS:-"10000"}
GUNICORN_MAX_REQUESTS_JITTER=${GUNICORN_MAX_REQUESTS_JITTER:-"1000"}
CMDPREFIX="${CMDPREFIX:-}"


if [ "${1:-}" == "--dev" ]; then
    echo "******************************************************************"
    echo "Running webapp in local dev environment."
    echo "Connect with your browser using: http://localhost:8000/ "
    echo "******************************************************************"
    cd /app/webapp/ && (node esbuild --watch & exec ${CMDPREFIX} python manage.py runserver 0.0.0.0:8000)

else
    exec ${CMDPREFIX} gunicorn \
        --pythonpath /app/webapp/ \
        --timeout "${GUNICORN_TIMEOUT}" \
        --workers="${GUNICORN_WORKERS}" \
        --worker-class="${GUNICORN_WORKER_CLASS}" \
        --max-requests="${GUNICORN_MAX_REQUESTS}" \
        --max-requests-jitter="${GUNICORN_MAX_REQUESTS_JITTER}" \
        --error-logfile=- \
        --access-logfile=- \
        --log-file=- \
        --config=/app/docker/config/gunicorn_config.py \
        --bind 0.0.0.0:"${PORT}" \
        crashstats.wsgi:application
fi
