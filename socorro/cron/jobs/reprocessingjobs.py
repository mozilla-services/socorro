#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pika

from configman import Namespace
from configman.converters import class_converter
from socorro.cron.base import PostgresTransactionManagedCronApp
from socorro.external.postgresql.dbapi2_util import execute_query_iter

_reprocessing_sql = """ DELETE FROM reprocessing_jobs RETURNING crash_id """


class ReprocessingJobsApp(PostgresTransactionManagedCronApp):
    app_name = 'reprocessing-jobs'
    app_description = (
        "Retrieves crash_ids from reprocessing_jobs and submits"
        "to the reprocessing queue"
    )
    app_version = '0.1'

    required_config = Namespace()
    required_config.add_option(
        'queue_class',
        default='socorro.external.rabbitmq.crashstorage.'
            'ReprocessingRabbitMQCrashStore',
        doc='class for inserting into the reprocessing queue',
        from_string_converter=class_converter
    )

    def __init__(self, config, info):
        super(ReprocessingJobsApp, self).__init__(config, ini)
        self.queue = self.config.queue_class(self.config)

    def run(self, connection):

        for crash_id in execute_query_iter(connection, _reprocessing_sql):
            self.queue.save_raw_crash(
                {'legacy_processing': True},
                [],
                crash_id
            )