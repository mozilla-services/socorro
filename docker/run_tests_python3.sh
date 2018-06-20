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
    socorro/unittest/lib/test_converters.py
    socorro/unittest/lib/test_datetimeutil.py
    socorro/unittest/lib/test_external_common.py
    socorro/unittest/lib/test_ooid.py
    socorro/unittest/lib/test_search_common.py
    socorro/unittest/lib/test_task_manager.py
    socorro/unittest/lib/test_threaded_task_manager.py
    socorro/unittest/lib/test_transform_rules.py
    socorro/unittest/lib/test_treelib.py
    socorro/unittest/lib/test_util.py
    socorro/unittest/lib/test_vertools.py
)

pytest ${WORKING_TESTS[@]}
