# Jenkins build script for running tests and packaging build
#
# Inspired by Zamboni
# https://github.com/mozilla/zamboni/blob/master/scripts/build.sh

# run unit tests
make clean
make coverage DB_USER=test DB_HOST=localhost DB_PASSWORD=aPassword

# pull pre-built, known version of breakpad
make clean
wget 'https://ci.mozilla.org/job/breakpad/lastSuccessfulBuild/artifact/breakpad.tar.gz'
tar -zxf breakpad.tar.gz
mv breakpad stackwalk

# package socorro.tar.gz for distribution
mkdir builds/
make install PREFIX=builds/socorro
tar -C builds --mode 755 --owner 0 --group 0 -zcf socorro.tar.gz socorro/
