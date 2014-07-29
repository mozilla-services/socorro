#!/bin/bash
# This script makes sure that Jenkins can properly run your tests against your
# codebase.
set -e

echo "Starting build on executor $EXECUTOR_NUMBER..."

source ${VIRTUAL_ENV:-"../socorro-virtualenv"}/bin/activate

# Make sure there's no old pyc files around.
find . -name '*.pyc' -exec rm {} \;

echo "Linting..."
git ls-files crashstats | xargs check.py | bin/linting.py

echo "Starting tests..."
FORCE_DB=true python manage.py test --noinput
echo "Tests finished."
