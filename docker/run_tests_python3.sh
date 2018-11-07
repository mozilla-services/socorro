#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# This script marks all the tests we know work in Python 3.
#
# Usage: ./docker/run_tests_python3.sh

# This is the list of known working tests by directory/filename. When you
# have tests in a directory/file working, add it to this list as a new line.
WORKING_TESTS=(
    socorro/signature/tests/test_*.py
    # socorro/unittest/app/test_*.py
    # socorro/unittest/cron/test_*.py
    # socorro/unittest/cron/jobs/test_*.py
    socorro/unittest/external/boto/test_*.py
    socorro/unittest/external/es/test_*.py
    socorro/unittest/external/fs/test_*.py
    socorro/unittest/external/postgresql/test_*.py
    socorro/unittest/external/rabbitmq/test_*.py
    socorro/unittest/lib/test_*.py
    # socorro/unittest/processor/test_*.py
    # socorro/unittest/processor/rules/test_*.py
    # socorro/unittest/scripts/test_*.py
)

# This is the list of known working tests by directory/filename for the webapp.
# The webapp is a separate test suite. When you have tests in a directory/file
# working, add it to this list as a new line.
WEBAPP_WORKING_TESTS=(
    # crashstats/api/tests/test_*.py
    # crashstats/authentication/tests/test_*.py
    # crashstats/base/tests/test_*.py
    # crashstats/crashstats/tests/test_*.py
    # crashstats/documentation/tests/test_*.py
    # crashstats/exploitability/tests/test_*.py
    # crashstats/graphics/tests/test_*.py
    # crashstats/manage/tests/test_*.py
    # crashstats/monitoring/tests/test_*.py
    # crashstats/profile/tests/test_*.py
    # crashstats/signature/tests/test_*.py
    # crashstats/sources/tests/test_*.py
    # crashstats/status/tests/test_*.py
    # crashstats/supersearch/tests/test_*.py
    # crashstats/tokens/tests/test_*.py
    # crashstats/topcrashers/tests/test_*.py
)

# Run socorro tests
pytest ${WORKING_TESTS[@]}

# If there are webapp tests to run, do this
if [ ${#WEBAPP_WORKING_TESTS[@]} -gt 0 ]; then
    # Collect static and run py.test in webapp
    pushd webapp-django
    "${WEBPACK_BINARY}" --mode=production --bail
    python manage.py collectstatic --noinput
    pytest ${WEBAPP_WORKING_TESTS[@]}
fi
