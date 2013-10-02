#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import Namespace
from socorro.lib.datetimeutil import utc_now
from socorro.database.database import singleRowSql, SQLDidNotReturnSingleRow
from socorro.cron.base import PostgresCronApp

"""
This script is what populates the aggregate server_status table for jobs and processors.

It provides up to date reports on the status of Socorro servers

The following fields are updated in server_status table:
  id - primary key
  date_recently_completed - timestamp for job most recently processed in jobs table
  date_oldest_job_queued - timestamp for the oldest job which is incomplete
  avg_process_sec - Average number of seconds (float) for jobs completed since last run
                    or 0.0 in edge case where no jobs have been processed
  avg_wait_sec- Average number of seconds (float) for jobs completed since last run
                or 0.0 in edge case where no jobs have been processed
  waiting_job_count - Number of jobs incomplete in queue
  processors_count - Number of processors running to process jobs
  date_created - timestamp for this record being udpated
"""
import time
import datetime

import psycopg2
import psycopg2.extras

import socorro.lib.util
from socorro.lib.datetimeutil import utc_now

_serverStatsSql = """ /* serverstatus.serverStatsSql */
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

    (
      SELECT
        MAX(r.completed_datetime)
      FROM %s r
    )
   AS date_recently_completed,

    (
      SELECT
        0
    )
    AS date_oldest_job_queued,

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
    AS avg_process_sec ,

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

    (
      SELECT
        '%s'
    )
    AS waiting_job_count,

    (
      SELECT
        count(processors.id)
      FROM processors
    )
    AS processors_count,

    CURRENT_TIMESTAMP AS date_created;
  """

_serverStatsLastUpdSql = """ /* serverstatus.serverStatsLastUpdSql */
    SELECT
      id,
      date_recently_completed,
      date_oldest_job_queued,
      avg_process_sec,
      avg_wait_sec,
      waiting_job_count,
      processors_count,
      date_created
    FROM server_status
    ORDER BY date_created DESC
    LIMIT 1;
"""

class ServerStatusCronApp(PostgresCronApp):
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
        default= _serverStatsSql,
        doc='Update the status of processors in Postgres DB'
    )
    required_config.add_option(
        'last_status_report_sql',
        default= _serverStatsLastUpdSql,
        doc='Return most recent status report in Postgres DB'
    )

    required_config = Namespace('rabbitmq')
    required_config.add_option(
        name='host',
        default='localhost',
        doc='the hostname of the RabbitMQ server',
    )
    required_config.add_option(
        name='virtual_host',
        default='/',
        doc='the name of the RabbitMQ virtual host',
    )
    required_config.add_option(
        name='port',
        default=5672,
        doc='the port for the RabbitMQ server',
    )
    required_config.add_option(
        name='rabbitmq_user',
        default='guest',
        doc='the name of the user within the RabbitMQ instance',
    )
    required_config.add_option(
        name='rabbitmq_password',
        default='guest',
        doc="the user's RabbitMQ password",
    )

    def _report_partition(self):
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
            rabbit_connection = self.config.queue_class(
                    self.config.rabbitmq
            ).connection()
            message_count = rabbit_connection.queue_status_standard.method.message_count
        except:
            raise

        try:
            # KeyError if it's never run successfully
            # TypeError if self.job_information is None
            last_run = self.job_information['last_success']
        except (KeyError, TypeError):
            last_run = utc_now()

        last_run_formatted = last_run.strftime('%Y-%m-%d')

        # We only ever run this for *now*, no backfilling
        current_partition = self._report_partition()
        query = self.config.update_sql % (
                current_partition,
                current_partition,
                current_partition,
                message_count)
        try:
            cursor = connection.cursor()
            cursor.execute(query)
            cursor.commit()
        except:
            cursor.rollback()

