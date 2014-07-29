#! /bin/bash -ex

rm -f pylint.txt
pylint -f parseable --rcfile=pylintrc socorro > pylint.txt
