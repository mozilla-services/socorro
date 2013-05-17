#!/bin/bash
#
# This script installs all dependencies, compiles static assets,
# and syncs the database. After it is run, the app should be runnable
# by WSGI.

VENV=./venv
git submodule update --init --recursive
npm install less
virtualenv --python=python2.6 .virtualenv
source .virtualenv/bin/activate
if [ ! -f crashstats/settings/local.py ]
then
    cp crashstats/settings/local.py-dist crashstats/settings/local.py
fi
if [ ! -d "$VENV/bin" ]; then
  echo "No virtualenv found.  Making one..."
  virtualenv $VENV --no-site-packages
  source $VENV/bin/activate
  pip install --upgrade pip
  pip install coverage
fi

pip install -q -r requirements/dev.txt

pip install -I --install-option="--home=`pwd`/vendor-local" \
    -r requirements/prod.txt
# because `python-ldap` is stupid and tries to re-install setuptools if you
# use the `-I` flag (aka `--ignore-installed`) we don't use it for
# `requirements/compiled.txt`
pip install --install-option="--home=`pwd`/vendor-local" \
    -r requirements/compiled.txt
export PATH=$PATH:./node_modules/.bin/
./manage.py collectstatic --noinput
./manage.py compress_jingo --force
./manage.py syncdb --noinput
