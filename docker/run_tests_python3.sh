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
    socorro/unittest/lib/*.py

    socorro/unittest/external/boto/*.py
    socorro/unittest/external/es/*.py
    socorro/unittest/external/postgresql/*.py
    socorro/unittest/external/rabbitmq/*.py

   socorro/unittest/database/*.py
)

pytest ${WORKING_TESTS[@]}
