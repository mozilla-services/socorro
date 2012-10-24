#!/bin/bash
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Jenkins build script for running tests and packaging build
#
# Inspired by Zamboni
# https://github.com/mozilla/zamboni/blob/master/scripts/build.sh

# any failures in this script should cause the build to fail
set -e

make clean

# copy default unit test configs
pushd socorro/unittest/config
for file in *.py.dist
do
  cp $file `basename $file .dist`
done
popd

# RHEL postgres 9 RPM installs pg_config here, psycopg2 needs it
export PATH=$PATH:/usr/pgsql-9.0/bin/
# run unit tests
make coverage DB_USER=test DB_HOST=localhost DB_PASSWORD=aPassword CITEXT="/usr/pgsql-9.0/share/contrib/citext.sql"

# pull pre-built, known version of breakpad
make clean
wget 'https://ci.mozilla.org/job/breakpad/lastSuccessfulBuild/artifact/breakpad.tar.gz'
tar -zxf breakpad.tar.gz
mv breakpad stackwalk

# package socorro.tar.gz for distribution
mkdir builds/
make install PREFIX=builds/socorro
make analysis
tar -C builds --mode 755 --owner 0 --group 0 -zcf socorro.tar.gz socorro/
