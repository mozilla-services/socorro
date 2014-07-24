#!/bin/bash
# This script makes sure that Jenkins can properly run your tests against your
# codebase.
set -e

echo "Starting build on executor $EXECUTOR_NUMBER..."

. ../socorro-virtualenv/bin/activate

# Make sure there's no old pyc files around.
find . -name '*.pyc' -exec rm {} \;

if [ ! -d "vendor" ]; then
    echo "No /vendor... crap."
    exit 1
fi

echo "Linting..."
git ls-files crashstats | xargs check.py | bin/linting.py

echo "Starting tests..."
FORCE_DB=true coverage run manage.py test --noinput --with-xunit
coverage xml $(find crashstats lib -name '*.py')
echo "Tests finished."
