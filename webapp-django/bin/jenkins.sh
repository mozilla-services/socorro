#!/bin/sh
# This script makes sure that Jenkins can properly run your tests against your
# codebase.
set -e

DB_HOST="localhost"
DB_USER="hudson"

VENV=$(CURDIR)/venv
[ -d $(VENV) ] || virtualenv -p python2.6 $(VENV)

echo "Starting build on executor $EXECUTOR_NUMBER..."

# Make sure there's no old pyc files around.
find . -name '*.pyc' -exec rm {} \;

# RHEL postgres 9 RPM installs pg_config here, psycopg2 needs it
export PATH=$PATH:/usr/pgsql-9.2/bin/

if [ ! -d "$VENV/bin" ]; then
  echo "No virtualenv found.  Making one..."
  virtualenv $VENV --no-site-packages
  source $VENV/bin/activate
  pip install --upgrade pip
  pip install coverage
fi

if [ ! -d "$WORKSPACE/webapp-django/vendor" ]; then
    echo "No /vendor... crap."
    exit 1
fi

source $VENV/bin/activate

pip install -q -r requirements/dev.txt

pip install -I --install-option="--home=`pwd`/vendor-local" \
    -r requirements/prod.txt
# because `python-ldap` is stupid and tries to re-install setuptools if you
# use the `-I` flag (aka `--ignore-installed`) we don't use it for
# `requirements/compiled.txt`
pip install --install-option="--home=`pwd`/vendor-local" \
    -r requirements/compiled.txt

cp crashstats/settings/local.py-dist crashstats/settings/local.py
echo "# enabled by force by jenkins.sh" >> crashstats/settings/local.py
echo "COMPRESS_OFFLINE = True" >> crashstats/settings/local.py

echo "Linting..."
find crashstats/ | grep '\.py$' | xargs check.py | grep -v "unable to detect undefined names" | awk '{ if ($0 ~ /[A-Za-z]/) { print; exit 1 } }'

echo "Starting tests..."
./manage.py collectstatic --noinput
# even though COMPRESS_OFFLINE=True is in before the tests are run
# COMPRESS becomes (not DEBUG) which will become False so that's why we need
# to use --force here.
./manage.py compress_jingo --force
FORCE_DB=true coverage run manage.py test --noinput --with-xunit
coverage xml $(find crashstats lib -name '*.py')
echo "Tests finished."

echo "Clean up..."
if [ -a "$WORKSPACE/socorro-crashstats.tar.gz" ]; then
    rm ./socorro-crashstats.tar.gz
fi
rm -rf $VENV

echo "Tar it..."
tar --mode 755 --owner 0 --group 0 --exclude-vcs -zcf ../socorro-crashstats.tar.gz ./*
mv ../socorro-crashstats.tar.gz ./

echo "FIN"
