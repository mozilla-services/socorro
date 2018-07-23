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
    socorro/unittest/lib/test_util.py
    socorro/unittest/lib/test_vertools.py

    socorro/unittest/external/boto/test_connection_context.py
    socorro/unittest/external/boto/test_crash_data.py
    socorro/unittest/external/boto/test_crashstorage.py
    socorro/unittest/external/boto/test_upload_telemetry_schema.py

    socorro/unittest/external/es/test_analyzers.py
    socorro/unittest/external/es/test_connection_context.py
    socorro/unittest/external/es/test_index_creator.py
    socorro/unittest/external/es/test_new_crash_source.py
    socorro/unittest/external/es/test_query.py

    socorro/unittest/external/postgresql/test_base.py
    socorro/unittest/external/postgresql/test_bugs.py
    socorro/unittest/external/postgresql/test_connection_context.py
    socorro/unittest/external/postgresql/test_crontabber_state.py
    socorro/unittest/external/postgresql/test_dbapi2_util.py
    socorro/unittest/external/postgresql/test_graphics_devices.py
    socorro/unittest/external/postgresql/test_platforms.py
    socorro/unittest/external/postgresql/test_product_build_types.py
    socorro/unittest/external/postgresql/test_releases.py
    socorro/unittest/external/postgresql/test_setupdb_app.py
    socorro/unittest/external/postgresql/test_signature_first_date.py

    socorro/unittest/external/rabbitmq/test_reprocessing.py
    socorro/unittest/external/rabbitmq/test_rmq_new_crash_source.py
)

pytest ${WORKING_TESTS[@]}
