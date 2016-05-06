#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from crontabber.base import BaseCronApp
from crontabber.mixins import (
    with_transactional_resource,
    using_postgres,
    with_postgres_connection_as_argument,
)
from socorro.external.postgresql.dbapi2_util import (
    execute_query_iter,
    execute_no_results,
)
from socorrolib.lib.util import DotDict


@using_postgres()
@with_postgres_connection_as_argument()
@with_transactional_resource(
    'socorro.external.rabbitmq.crashstorage.ReprocessingRabbitMQCrashStore',
    'queuing'
)
class ReprocessingJobsApp(BaseCronApp):
    app_name = 'reprocessing-jobs'
    app_description = (
        "Retrieves crash_ids from reprocessing_jobs and submits"
        "to the reprocessing queue"
    )
    app_version = '0.1'

    def run(self, connection):
        select_sql = """
            SELECT crash_id FROM reprocessing_jobs LIMIT 10000
        """
        crash_ids = []
        for crash_id, in execute_query_iter(connection, select_sql):
            crash_ids.append(crash_id)

        delete_sql = """
            DELETE from reprocessing_jobs WHERE crash_id = %(crash_id)s
        """

        for crash_id in crash_ids:
            self.queuing_connection_factory.save_raw_crash(
                DotDict({'legacy_processing': 0}),
                [],
                crash_id
            )
            execute_no_results(connection, delete_sql, {
                'crash_id': crash_id
            })
            connection.commit()
