#!/bin/bash
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# This script runs migrations for Socorro. Run this in a crontabber docker
# container.

# Get a datestamp
date

# Run Django migrations
python webapp-django/manage.py migrate --no-input

# Run Alembic migrations
alembic -c docker/config/alembic.ini upgrade head
