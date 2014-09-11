#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from crontabber.base import BaseCronApp
from crontabber.mixins import (
    with_postgres_transactions,
    with_single_postgres_transaction,
    with_transactional_resource
)
from socorro.external.postgresql.dbapi2_util import execute_query_iter
from socorro.lib.util import DotDict

_reprocessing_sql = """ DELETE FROM reprocessing_jobs RETURNING crash_id """


@with_postgres_transactions()
@with_single_postgres_transaction()
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

        for crash_id, in execute_query_iter(connection, _reprocessing_sql):
            self.queuing_connection_factory.save_raw_crash(
                DotDict({'legacy_processing': 0}),
                [],
                crash_id
            )
