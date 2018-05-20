#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs tests.
#
# This should be called from inside a container and after the dependent
# services have been launched. It depends on:
#
# * elasticsearch
# * postgresql
# * rabbitmq

# Failures should cause setup to fail
set -v -e -x

# Set up environment variables

# NOTE(willkg): This has to be "database_url" all lowercase because configman.
DATABASE_URL=${database_url:-"postgres://postgres:aPassword@postgresql:5432/socorro_test"}

# NOTE(willkg): This has to be "elasticsearch_url" all lowercase because configman.
ELASTICSEARCH_URL=${elasticsearch_url:-"http://elasticsearch:9200"}

export PYTHONPATH=/app/:$PYTHONPATH
FLAKE8="$(which flake8)"
PYTEST="$(which pytest)"
PYTHON="$(which python)"
ALEMBIC="$(which alembic)"
SETUPDB="/app/socorro/external/postgresql/setupdb_app.py"

# Wait for postgres and elasticsearch services to be ready
urlwait "${DATABASE_URL}" 10
urlwait "${ELASTICSEARCH_URL}" 10

# Set up socorro_migration_test db for migration testing
"${PYTHON}" "${SETUPDB}" --database_name=socorro_migration_test --dropdb --logging.level=40 --unlogged --createdb

# Set up socorro_test db for unittests
"${PYTHON}" "${SETUPDB}" --database_name=socorro_test --dropdb --logging.level=40 --unlogged --no_staticdata --createdb

# Test the last migration
"${ALEMBIC}" -c "${alembic_config}" downgrade -1
"${ALEMBIC}" -c "${alembic_config}" upgrade heads

# Run linting
"${FLAKE8}"

if [ "${USEPYTHON:-2}" == "2" ]; then
    # Run tests
    "${PYTEST}"

    # Collect static and then run py.test in the webapp
    pushd webapp-django
    python manage.py collectstatic --noinput
    "${PYTEST}"
    popd
else
    # Run the tests we know work in Python 3
    ./docker/run_tests_python3.sh
fi
