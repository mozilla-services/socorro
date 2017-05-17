#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs tests.

# Failures should cause setup to fail
set -v -e -x

# Set up environment variables

export PYTHONPATH=/app/:$PYTHONPATH
NOSE="$(which nosetests)"
ALEMBIC="$(which alembic)"
SETUPDB="$(which python) /app/socorro/external/postgresql/setupdb_app.py"

# FIXME(willkg): Tests fail if /app/config/alembic.ini doesn't exist. But
# hit permission error when creating it.
# Create necessary .ini files
#if [ ! -f /app/config/alembic.ini ]; then
#    cp /app/config/alembic.ini-dist /app/config/alembic.ini
#fi

# Verify we have __init__.py files everywhere we need them
errors=0
while read d
do
  if [ ! -f "$d/__init__.py" ]
  then
    if [ "$(ls -A $d/test*py)" ]
    then
        echo "$d is missing an __init__.py file, tests will not run"
        errors=$((errors+1))
    else
        echo "$d has no tests - ignoring it"
    fi
  fi
done < <(find socorro/unittest/* -not -name logs -type d)

if [ $errors != 0 ]
then
  exit 1
fi

# Wait for postgres in the postgres container to be ready
urlwait $database_url 10

# Wait for elasticsearch in the elasticsearch container to be ready
urlwait $elasticsearch_url 10

# Set up database for alembic migrations
#
# FIXME(willkg): For some reason, this has to go first because setting up
# socorro_integration_test needs it. Does it mean that alembic is doing
# migrations in the wrong db?
$SETUPDB --database_name=socorro_migration_test --dropdb --logging.stderr_error_logging_level=40 --unlogged --createdb

# Set up database for unittests
$SETUPDB --database_name=socorro_integration_test --dropdb --logging.stderr_error_logging_level=40 --unlogged --no_staticdata --createdb

# FIXME(willkg): What's this one for? It's got crontabber stuff in it and that's
# it. Maybe we don't need it?
$SETUPDB --database_name=socorro_test --dropdb --no_schema --logging.stderr_error_logging_level=40 --unlogged --no_staticdata --createdb

$ALEMBIC -c config/alembic.ini downgrade -1
$ALEMBIC -c config/alembic.ini upgrade heads

# Run tests
$NOSE socorro -s

# Collect static and then test webapp
pushd webapp-django
python manage.py collectstatic --noinput
./bin/ci.sh
popd
