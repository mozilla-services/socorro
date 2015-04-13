#! /bin/bash

echo "this is clean.sh"

find ./ -type f -name "*.pyc" -exec rm {} \;
rm -rf ./google-breakpad/ ./build/ ./breakpad/ ./stackwalk breakpad.tar.gz

pushd minidump-stackwalk
make clean
popd
