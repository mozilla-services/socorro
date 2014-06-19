#!/bin/bash
#
# This script installs all dependencies, compiles static assets,
# and syncs the database. After it is run, the app should be runnable
# by WSGI.
set -e

. ../socorro-virtualenv/bin/activate

if [ ! -f crashstats/settings/local.py ]
then
    cp crashstats/settings/prod.py-dist crashstats/settings/local.py
fi

export PATH=$PATH:./node_modules/.bin/

if [ -n "$WORKSPACE" ]
then
    # this means we're running jenkins
    cp crashstats/settings/prod.py-dist crashstats/settings/local.py
    echo "# force jenkins.sh" >> crashstats/settings/local.py
    echo "COMPRESS_OFFLINE = True" >> crashstats/settings/local.py
    # when running tests you have to have LocMemCache
    cat >> crashstats/settings/local.py <<EOL
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake'
    }
}
EOL
fi

./manage.py collectstatic --noinput
# even though COMPRESS_OFFLINE=True COMPRESS becomes (not DEBUG) which
# will become False so that's why we need to use --force here.
./manage.py compress_jingo --force
./manage.py syncdb --noinput
