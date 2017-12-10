#! /bin/bash

echo "this is clean.sh"

# Remove .pyc files
find ./ -type f -name "*.pyc" -exec rm {} \;

# Remove any mdsw build artifacts
rm -rf ./google-breakpad/ ./build/ ./breakpad/ ./stackwalk breakpad.tar.gz
pushd minidump-stackwalk
make clean
popd
