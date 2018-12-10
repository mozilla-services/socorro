#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# This script marks all the tests we know work in Python 3.
#
# Usage: ./docker/run_tests_python3.sh

# Failures should cause this script to stop
set -v -e -x

# Run socorro tests
pytest

# Collect static and run py.test in webapp
pushd webapp-django
"${WEBPACK_BINARY}" --mode=production --bail
python manage.py collectstatic --noinput
pytest
popd
