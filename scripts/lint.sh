#! /bin/bash

PYLINT=$VIRTUALENV/bin/pylint

rm -f pylint.txt
$PYLINT -f parseable --rcfile=pylintrc socorro > pylint.txt
