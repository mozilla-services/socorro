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
    ( SELECT MAX(r.completed_datetime) FROM %s r )
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
      FROM %s r
      WHERE r.completed_datetime > %%s
    )
        AS avg_process_sec,

    (
      SELECT COALESCE (
        EXTRACT (
          EPOCH FROM avg(r.completed_datetime - r.date_processed)
        ),
        0
      )
      FROM %s r
      WHERE r.completed_datetime > %%s
    )
        AS avg_wait_sec,

    '%s'::int
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
    app_description = 'Server Status'
    app_version = '0.1'

    required_config = Namespace()
    required_config.add_option(
        'queue_class',
        default='socorro.external.rabbitmq.connection_context.ConnectionContext',
        doc='Queue class for fetching status/queue depth'
    )
    required_config.add_option(
        'update_sql',
        default=_server_stats_sql,
        doc='Update the status of processors in Postgres DB'
    )
    required_config.add_option(
        'processing_interval_seconds',
        default=5 * 60,
        doc='How often we process reports (in seconds)'
    )

    def _report_partition(self):
        now = utc_now()
        previous_monday = now - datetime.timedelta(now.weekday())
        reports_partition = 'reports_%4d%02d%02d' % (
            previous_monday.year,
            previous_monday.month,
            previous_monday.day,
        )
        return reports_partition

    def run(self, connection):
        logger = self.config.logger

        try:
            rabbit_connection = self.config.\
                queue_class(self.config)
            message_count = rabbit_connection.\
                connection().queue_status_standard.\
                method.message_count
        except:
            logger.info('Failed to get message count from RabbitMQ')
            return

        start_time = datetime.datetime.now()
        start_time -= datetime.timedelta(seconds=self.config.processing_interval_seconds)

        current_partition = self._report_partition()
        query = self.config.update_sql % (
            current_partition,
            current_partition,
            current_partition,
            message_count)
        try:
            cursor = connection.cursor()
            cursor.execute(query, (start_time, start_time))
        except:
            logger.info('Failed to update server status at %s', start_time)
            return
