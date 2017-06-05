#!/bin/bash
# This script makes sure that Jenkins can properly run your tests against your
# codebase.
set -e

echo "Starting build on executor $EXECUTOR_NUMBER..."

# When we're running in a docker environment, we don't need the
# virtualenv, so we can skip this.
if [ "$1" != "--docker" ]; then
    source ${VIRTUAL_ENV:-"../socorro-virtualenv"}/bin/activate
fi

# Make sure there's no old pyc files around.
find . -name '*.pyc' -exec rm {} \;

echo "Linting..."
git ls-files crashstats | grep '\.py$' | xargs flake8 | bin/linting.py

echo "Starting tests..."
export SECRET_KEY="doesn't matter, tests"
export CACHE_BACKEND="django.core.cache.backends.locmem.LocMemCache"
export CACHE_LOCATION="crashstats"
export OLD_PYTHONPATH=$PYTHONPATH
export PYTHONPATH=../:$PYTHONPATH
FORCE_DB=true python manage.py test --noinput
export PYTHONPATH=$OLD_PYTHONPATH
echo "Tests finished."
