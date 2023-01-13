#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: bin/setup_postgres.sh
#
# Sets up postgres tables.

# Note: This deletes existing tables and all their data and recreates the
# database.
#
# Note: This should be called from inside a container.

set -euo pipefail

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
cd /app/webapp
python manage.py migrate auth
python manage.py migrate

# Add initial data from fixtures
echo "Adding fixture data..."
python manage.py loaddata platforms
