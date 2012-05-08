# Jenkins build script for running tests and packaging build
#
# Inspired by Zamboni
# https://github.com/mozilla/zamboni/blob/master/scripts/build.sh

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
tar -C builds --mode 755 --owner 0 --group 0 -zcf socorro.tar.gz socorro/
