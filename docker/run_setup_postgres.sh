#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Sets up postgres tables, stored procedures, and such.

# This should get run only to initialize Postgres and probably only in local
# development environments.

cd /app

# This is a webapp environment variable. If it doesn't exist, then use
# "breakpad"
DATABASE="${DATASERVICE_DATABASE_NAME:-breakpad}"

# Wait until postgres is listening
urlwait "${DATABASE_URL}" 10

# FIXME(willkg): Make this idempotent so it doesn't affect anything if run
# multiple times
# NOTE(willkg): add --dropdb to this if you want to recreate the db
echo "Setting up the db (${DATABASE}) and generating fake data..."
./scripts/socorro setupdb \
                  --database_name="${DATABASE}" \
                  --fakedata \
                  --fakedata_days=3 \
                  --createdb

# This does Django migrations and is idempotent
echo "Setting up the db for Django..."
cd /app/webapp-django
python manage.py migrate auth
python manage.py migrate
