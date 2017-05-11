#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs the webapp.

PORT=${PORT:-"8000"}
NUM_WORKERS=${NUM_WORKERS:-"6"}

uwsgi --pythonpath /app/socorro/webapp-django/ \
      --master \
      --need-app \
      --wsgi webapp-django.wsgi.socorro-crashstats \
      --buffer-size 16384 \
      --enable-threads \
      --processes $NUM_WORKERS \
      --http-socket 0.0.0.0:${PORT}
