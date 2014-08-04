#! /bin/bash

find ./ -type f -name "*.pyc" -exec rm {} \;
rm -rf ./google-breakpad/ ./builds/ ./breakpad/ ./stackwalk
rm -rf ./breakpad.tar.gz ./apache-maven-3.2.2-bin.tar.gz

pushd minidump-stackwalk
make clean
popd
