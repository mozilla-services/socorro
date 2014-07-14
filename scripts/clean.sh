#! /bin/bash

find ./ -type f -name "*.pyc" -exec rm {} \;
rm -rf ./google-breakpad/ ./builds/ ./breakpad/ ./stackwalk
rm -rf ./breakpad.tar.gz
cd minidump-stackwalk; make clean
