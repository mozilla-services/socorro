#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

set -e

# Sets up postgres tables, stored procedures, types, and such.

# NOTE: This should only be run if you want to drop an existing database and
# create a new one from scratch for a development environment.

cd /app

# This is a webapp environment variable. If it doesn't exist, then use
# "breakpad"
DATABASE="${DATASERVICE_DATABASE_NAME:-breakpad}"

# Wait until postgres is listening
urlwait "${DATABASE_URL}" 10

# This drops and re-creates the db; the --dropdb code will prompt the user
# before it does anything giving the user a chance to do a "oh no--don't do
# that!" kind of thing
echo "Dropping existing db and creating new db named (${DATABASE})..."
./socorro/external/postgresql/setupdb_app.py \
                  --database_name="${DATABASE}" \
                  --dropdb \
                  --createdb

# Run Django migrations
echo "Setting up the db for Django..."
cd /app/webapp-django
python manage.py migrate auth
python manage.py migrate
