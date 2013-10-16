#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
This job populates the server_status table for RabbitMQ and processors.

The following fields are updated in server_status table:
    id - primary key
    date_recently_completed - timestamp for job most recently processed in jobs
        table
    date_oldest_job_queued - (INACCURATE until we upgrade RabbitMQ) timestamp
        for the oldest job which is incomplete
    avg_process_sec - Average number of seconds (float) for jobs completed
        since last run or 0.0 in edge case where no jobs have been processed
    avg_wait_sec- Average number of seconds (float) for jobs completed since
        last run
        or 0.0 in edge case where no jobs have been processed
    waiting_job_count - Number of jobs in queue, not assigned to a processor
    processors_count - Number of processors running to process jobs
    date_created - timestamp for this record being udpated
"""

import datetime

from configman import Namespace
from configman.converters import class_converter

from socorro.lib.datetimeutil import utc_now
from socorro.cron.base import PostgresTransactionManagedCronApp

_server_stats_sql = """
  INSERT INTO server_status (
    date_recently_completed,
    date_oldest_job_queued,
    avg_process_sec,
    avg_wait_sec,
    waiting_job_count,
    processors_count,
    date_created
  )
  SELECT
    ( SELECT MAX(r.completed_datetime) FROM %(table)s r )
        AS date_recently_completed,

    Null
        AS date_oldest_job_queued, -- Need RabbitMQ upgrade to get this info

    (
      SELECT COALESCE (
        EXTRACT (
          EPOCH FROM avg(r.completed_datetime - r.started_datetime)
        ),
        0
      )
      FROM %(table)s r
      WHERE r.completed_datetime > %%(start_time)s
    )
        AS avg_process_sec,

    (
      SELECT COALESCE (
        EXTRACT (
          EPOCH FROM avg(r.completed_datetime - r.date_processed)
        ),
        0
      )
      FROM %(table)s r
      WHERE r.completed_datetime > %%(start_time)s
    )
        AS avg_wait_sec,

    %(count)s
        AS waiting_job_count, -- From RabbitMQ

    (
      SELECT
        count(processors.id)
      FROM processors
    )
    AS processors_count,

    CURRENT_TIMESTAMP AS date_created
  """


class ServerStatusCronApp(PostgresTransactionManagedCronApp):
    app_name = 'server-status'
    app_description = (
        "Connects to the message queue and investigates "
        "the recent reports and processor activity in the database"
    )
    app_version = '0.1'

    required_config = Namespace()
    required_config.add_option(
        'queue_class',
        default='socorro.external.rabbitmq.connection_context.ConnectionContext',
        doc='Queue class for fetching status/queue depth',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'processing_interval_seconds',
        default=5 * 60,
        doc='How often we process reports (in seconds)'
    )

    def _report_partition(self):
        now = utc_now()
        previous_monday = now - datetime.timedelta(now.weekday())
        reports_partition = 'reports_' + previous_monday.strftime('%Y%m%d')
        return reports_partition

    def run(self, connection):
        logger = self.config.logger

        rabbit_connection = self.config.queue_class(self.config)
        message_count = int(
            rabbit_connection.connection()
            .queue_status_standard
            .method.message_count
        )

        start_time = datetime.datetime.utcnow()
        start_time -= datetime.timedelta(
            seconds=self.config.processing_interval_seconds
        )

        current_partition = self._report_partition()
        query = _server_stats_sql % {
            'table': self._report_partition(),
            'count': message_count
        }
        cursor = connection.cursor()
        cursor.execute(query, {'start_time': start_time})

