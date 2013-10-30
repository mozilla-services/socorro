#!/bin/bash
#
# This script installs all dependencies, compiles static assets,
# and syncs the database. After it is run, the app should be runnable
# by WSGI.
set -e

VENV=./virtualenv

if [ ! -f bixie/settings/local.py ]
then
    cp bixie/settings/local.py-dist bixie/settings/local.py
fi
if [ ! -d "$VENV/bin" ]; then
  echo "No virtualenv found.  Making one..."
  virtualenv $VENV --python=python2.6
  source $VENV/bin/activate
  pip install --upgrade pip
  pip install coverage
fi

source $VENV/bin/activate

time pip install -q -r requirements/dev.txt

time pip install --install-option="--home=`pwd`/vendor-local" \
    -r requirements/prod.txt
time pip install --install-option="--home=`pwd`/vendor-local" \
    -r requirements/compiled.txt

export PATH=$PATH:./node_modules/.bin/

if [ -n "$WORKSPACE" ]
then
    # this means we're running jenkins
    cp bixie/settings/local.py-dist bixie/settings/local.py
    echo "# force jenkins.sh" >> bixie/settings/local.py
    echo "COMPRESS_OFFLINE = True" >> bixie/settings/local.py
fi

./manage.py collectstatic --noinput
# even though COMPRESS_OFFLINE=True COMPRESS becomes (not DEBUG) which
# will become False so that's why we need to use --force here.
./manage.py compress_jingo --force
./manage.py syncdb --noinput
