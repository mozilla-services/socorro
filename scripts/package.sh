#! /bin/bash -e

##
# Args
#  1: Version of socorro to release
#  2: Type of package to build
##
VERSION=${1:-$(git describe --tags | cut -d'-' -f1)}
TYPE=${2:-"rpm"}
# PREFIX will have any 'socorro' directory suffix removed
PREFIX=${PREFIX:-"/data"}
DESC="A distributed system for collecting, processing,
 and displaying crash reports from clients using Breakpad"

if [ ! -d 'builds/socorro' ]; then
    echo "Socorro has not been built (build/socorro does not exist)."
    echo "  Please run './scripts/build.sh' before continuing."
    exit 1
fi
cd builds

echo "> Building Socorro $VERSION ..."
fpm -s dir -t $TYPE \
    -v $VERSION \
    -n "socorro" \
    -m "<socorro-dev@mozilla.com>" \
    --epoch $VERSION \
    --prefix ${PREFIX%%"socorro"} \
    --license "MPL" \
    --vendor "Mozilla" \
    --url "https://wiki.mozilla.org/Socorro" \
    --description "$DESC" \
    --before-install ../scripts/package/before-install.sh \
    --after-install ../scripts/package/after-install.sh \
    socorro

echo "> Build Complete."
