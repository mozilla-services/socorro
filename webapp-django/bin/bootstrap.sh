#!/bin/bash
#
# This script installs all dependencies, compiles static assets,
# and syncs the database. After it is run, the app should be runnable
# by WSGI.
set -e

source ${VIRTUAL_ENV:-"../socorro-virtualenv"}/bin/activate

export PATH=$PATH:./node_modules/.bin/
export SECRET_KEY="doesn't matter, tests"

# See https://bugzilla.mozilla.org/show_bug.cgi?id=1314258
# When the collectstatic command is run, it needs to have all the
# config set from consulate. But because we don't know how to do
# that here, we instead set it temporarily here in this build script.
# NOTE! This is NOT a sensitive key/secret.
export GOOGLE_ANALYTICS_ID="UA-35433268-50"

echo "Install the node packages"
npm install

echo "Running collectstatic"
# XXX Should this do something like `rm -fr static; mkdir static`?
./manage.py collectstatic --noinput
