#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs the webapp.
#
# Use the "--dev" argument to run the webapp in a docker container for
# local development.

set -e

PORT=${PORT:-"8000"}
GUNICORN_WORKERS=${GUNICORN_WORKERS:-"1"}
GUNICORN_WORKER_CLASS=${GUNICORN_WORKER_CLASS:-"sync"}
GUNICORN_MAX_REQUESTS=${GUNICORN_MAX_REQUESTS:-"10000"}
GUNICORN_MAX_REQUESTS_JITTER=${GUNICORN_MAX_REQUESTS_JITTER:-"1000"}


if [ "$1" == "--dev" ]; then
    echo "******************************************************************"
    echo "Running webapp in local dev environment."
    echo "Connect with your browser using: http://localhost:8000/ "
    echo "******************************************************************"
    cd /app/webapp-django/ && ${CMDPREFIX} python manage.py runserver 0.0.0.0:8000

else
    echo "GUNICORN_WORKERS=${GUNICORN_WORKERS}"
    echo "GUNICORN_WORKER_CLASS=${GUNICORN_WORKER_CLASS}"
    echo "GUNICORN_MAX_REQUESTS=${GUNICORN_MAX_REQUESTS}"
    echo "GUNICORN_MAX_REQUESTS_JITTER=${GUNICORN_MAX_REQUESTS_JITTER}"
    echo "PORT=${PORT}"
    ${CMDPREFIX} gunicorn \
        --pythonpath /app/webapp-django/ \
        --workers="${GUNICORN_WORKERS}" \
        --worker-class="${GUNICORN_WORKER_CLASS}" \
        --max-requests="${GUNICORN_MAX_REQUESTS}" \
        --max-requests-jitter="${GUNICORN_MAX_REQUESTS_JITTER}" \
        --error-logfile=- \
        --access-logfile=- \
        --log-file=- \
        --config=/app/docker/config/gunicorn_config.py \
        --bind 0.0.0.0:"${PORT}" \
        webapp-django.wsgi.socorro-crashstats:application
fi
