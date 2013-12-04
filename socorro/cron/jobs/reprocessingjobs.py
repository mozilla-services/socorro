#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

import pika

from configman import Namespace
from configman.converters import class_converter
from socorro.lib.datetimeutil import utc_now
from socorro.cron.base import PostgresTransactionManagedCronApp

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
        default='socorro.external.rabbitmq.connection_context.ConnectionContext',
        doc='Queue class reprocessing queue',
        from_string_converter=class_converter
    )

    def run(self, connection):
        logger = self.config.logger

        _basic_properties = pika.BasicProperties(
            delivery_mode=2,  # make message persistent
        )

        rabbit_connection = self.config.queue_class(self.config)

        cursor = connection.cursor()
        cursor.execute(_reprocessing_sql)
        try:
            for crash_id in cursor.fetchone():
                rabbit_connection.channel.basic_publish(
                    exchange='',
                    routing_key=rabbit_connection.config.reprocessing_queue_name,
                    body=crash_id,
                    properties=_basic_properties
                )

        except Exception as e:
            # No results found, and that's ok
            raise e

        connection.commit()
