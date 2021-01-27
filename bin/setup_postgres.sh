#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

set -e

# Sets up postgres tables.

# NOTE: This should only be run if you want to drop an existing database and
# create a new one from scratch for a development environment.

cd /app

# This is a webapp environment variable. If it doesn't exist, then use
# "breakpad".
DATABASE="${DATASERVICE_DATABASE_NAME:-breakpad}"

# Wait until postgres is listening
urlwait "${DATABASE_URL}" 10

# Drop and create the database
echo "Dropping and creating db..."
./socorro-cmd db drop || true
./socorro-cmd db create || true

# Run Django migrations
echo "Setting up tables..."
cd /app/webapp-django
python manage.py migrate auth
python manage.py migrate

# Add initial data from fixtures
echo "Adding fixture data..."
python manage.py loaddata platforms
