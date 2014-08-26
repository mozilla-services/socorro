#! /bin/bash -e

##
# Args
#  1: Version of socorro to release
#  2: Type of package to build
##
VERSION=${1:-$(git describe --tags | cut -d'-' -f1)}
TYPE=${2:-"deb"}

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
    -m "<socorro-dev@mozilla.com>"
    --license "MPL" \
    --url "https://wiki.mozilla.org/Socorro"
    socorro

echo "> Build Complete."
