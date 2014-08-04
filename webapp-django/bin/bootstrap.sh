#!/bin/bash
#
# This script installs all dependencies, compiles static assets,
# and syncs the database. After it is run, the app should be runnable
# by WSGI.
set -e

source ${VIRTUAL_ENV:-"../socorro-virtualenv"}/bin/activate

if [ ! -f crashstats/settings/local.py ]
then
    cp crashstats/settings/local.py-dist crashstats/settings/local.py
fi

export PATH=$PATH:./node_modules/.bin/

if [ -n "$WORKSPACE" ]
then
    # this means we're running jenkins
    cp crashstats/settings/local.py-dist crashstats/settings/local.py
    echo "# force jenkins.sh" >> crashstats/settings/local.py
    echo "COMPRESS_OFFLINE = True" >> crashstats/settings/local.py
fi

./manage.py collectstatic --noinput
# even though COMPRESS_OFFLINE=True COMPRESS becomes (!DEBUG) which
# will become False so that's why we need to use --force here.
./manage.py compress --force --engine=jinja2
./manage.py syncdb --noinput
