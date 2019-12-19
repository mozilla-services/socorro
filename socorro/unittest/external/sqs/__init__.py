# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import ConfigurationManager, environment

from socorro.external.sqs.crashqueue import SQSCrashQueue


# Visibility timeout for the AWS SQS queue in seconds
VISIBILITY_TIMEOUT = 1


def get_sqs_config():
    sqs_config = SQSCrashQueue.get_required_config()
    config_manager = ConfigurationManager(
        [sqs_config],
        app_name="test-sqs",
        app_description="",
        values_source_list=[environment],
        argv_source=[],
    )
    return config_manager.get_config()
