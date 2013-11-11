#!/bin/bash
# run tests and prepare an installation
set -e

libexec=$(dirname "$0")

echo "--> bootstrap:"
"$libexec/bootstrap.sh" "$@" || exit 1

if [ -z "$VENV" ]
then
  VENV=./virtualenv
fi
source $VENV/bin/activate

time pip install --install-option="--home=`pwd`/vendor-local" \
    -r requirements/prod.txt
time pip install --install-option="--home=`pwd`/vendor-local" \
    -r requirements/compiled.txt

echo "--> tests:"
"$libexec/jenkins-tests.sh" "$@" || exit 1

echo "FIN"
