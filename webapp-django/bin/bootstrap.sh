#!/bin/bash
#
# This script installs all dependencies, compiles static assets,
# and syncs the database. After it is run, the app should be runnable
# by WSGI.
set -e

source ${VIRTUAL_ENV:-"../socorro-virtualenv"}/bin/activate

export PATH=$PATH:./node_modules/.bin/
export SECRET_KEY="doesn't matter, tests"

if [ -n "$WORKSPACE" ]
then
    # this means we're running jenkins, force compression
    # FIXME we need a better way to determine if this is a release build!
    export COMPRESS_ENABLED=True
    export COMPRESS_OFFLINE=True
fi

./manage.py collectstatic --noinput
# even though COMPRESS_OFFLINE=True COMPRESS becomes (!DEBUG) which
# will become False so that's why we need to use --force here.
./manage.py compress --force --engine=jinja2
