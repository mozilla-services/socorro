#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Sets up postgres tables, stored procedures, and such.

# This should get run only to initialize Postgres and probably only in local
# development environments.

cd /app

# FIXME(willkg): Make this idempotent so that running it after it's already been
# run doesn't affect anything.
echo "Setting up the db..."
./scripts/socorro setupdb \
                  --database_name=breakpad \
                  --fakedata \
                  --fakedata_days=3 \
                  --createdb

# This does Django migrations. It's idempotent.
echo "Setting up the db for Django..."
cd /app/webapp-django
python manage.py migrate auth
python manage.py migrate
