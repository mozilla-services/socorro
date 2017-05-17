#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs the webapp.
#
# Use the "--dev" argument to run the webapp in a docker container for
# the purposes of local development.

BUFFER_SIZE=${BUFFER_SIZE:-"16384"}
PORT=${PORT:-"8000"}
NUM_WORKERS=${NUM_WORKERS:-"6"}

if [ "$1" == "--dev" ]; then
    # Collect static files
    cd /app/webapp-django/ && python manage.py collectstatic --noinput

    # Run with manage.py
    echo "Running webapp. Connect with browser using http://localhost:8000/ ."
    cd /app/webapp-django/ && python manage.py runserver 0.0.0.0:8000

else
    # Run uwsgi
    uwsgi --pythonpath /app/webapp-django/ \
          --master \
          --need-app \
          --wsgi webapp-django.wsgi.socorro-crashstats \
          --buffer-size ${BUFFER_SIZE} \
          --enable-threads \
          --processes ${NUM_WORKERS} \
          --http-socket 0.0.0.0:${PORT}
fi
