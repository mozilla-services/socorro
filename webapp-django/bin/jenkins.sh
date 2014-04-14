#!/bin/bash
# run tests and prepare an installation
set -e

libexec=$(dirname "$0")

echo "--> bootstrap:"
"$libexec/bootstrap.sh" "$@" || exit 1

echo "--> tests:"
"$libexec/jenkins-tests.sh" "$@" || exit 1

echo "FIN"
