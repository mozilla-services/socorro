#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs the webapp.
#
# Use the "--dev" argument to run the webapp in a docker container for
# the purposes of local development.

set -e

BUFFER_SIZE=${BUFFER_SIZE:-"16384"}
PORT=${PORT:-"8000"}
NUM_WORKERS=${NUM_WORKERS:-"6"}

# If this was kicked off via docker-compose, then it has a behavior
# configuration already. If it wasn't, then we need to add behavior
# configuration to the environment.
if [[ -z "${WEBAPP_BEHAVIOR}" ]];
then
    echo "Pulling in webapp behavior configuration..."
    CMDPREFIX="/app/bin/build_env.py /app/docker/config/webapp.env"
else
    echo "Already have webapp behavior configuration..."
    CMDPREFIX=
fi

if [ "$1" == "--dev" ]; then
    # Run with manage.py
    echo "Running webapp. Connect with browser using http://localhost:8000/ ."
    cd /app/webapp-django/ && ${CMDPREFIX} python manage.py runserver 0.0.0.0:8000

else
    # Run uwsgi
    ${CMDPREFIX} uwsgi --pythonpath /app/webapp-django/ \
                 --master \
                 --need-app \
                 --wsgi webapp-django.wsgi.socorro-crashstats \
                 --buffer-size "${BUFFER_SIZE}" \
                 --enable-threads \
                 --processes "${NUM_WORKERS}" \
                 --http-socket 0.0.0.0:"${PORT}"
fi
