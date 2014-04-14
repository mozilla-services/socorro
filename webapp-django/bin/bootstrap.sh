#!/bin/bash
#
# This script installs all dependencies, compiles static assets,
# and syncs the database. After it is run, the app should be runnable
# by WSGI.
set -e

VENV=./virtualenv

if [ ! -f crashstats/settings/local.py ]
then
    cp crashstats/settings/local.py-dist crashstats/settings/local.py
fi
if [ ! -d "$VENV/bin" ]; then
  echo "No virtualenv found.  Making one..."
  virtualenv $VENV --python=python2.6
  source $VENV/bin/activate
  pip install --upgrade pip
  pip install coverage
fi

source $VENV/bin/activate

pip install -r requirements.txt

export PATH=$PATH:./node_modules/.bin/

if [ -n "$WORKSPACE" ]
then
    # this means we're running jenkins
    cp crashstats/settings/local.py-dist crashstats/settings/local.py
    echo "# force jenkins.sh" >> crashstats/settings/local.py
    echo "COMPRESS_OFFLINE = True" >> crashstats/settings/local.py
fi

./manage.py collectstatic --noinput
# even though COMPRESS_OFFLINE=True COMPRESS becomes (not DEBUG) which
# will become False so that's why we need to use --force here.
./manage.py compress_jingo --force
./manage.py syncdb --noinput
