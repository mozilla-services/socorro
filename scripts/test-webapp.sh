#! /bin/bash -ex

echo "this is test-webapp.sh"

source scripts/defaults

# test webapp
pushd webapp-django
./bin/ci.sh
popd
