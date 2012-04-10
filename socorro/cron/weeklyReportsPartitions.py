#!/usr/bin/env python

import logging
logger = logging.getLogger("weeklyReportsPartitions")

from configman import Namespace, class_converter
from socorro.database.transaction_executor import (
  TransactionExecutorWithInfiniteBackoff)
from socorro.external.postgresql.connection_context import ConnectionContext
from socorro.app.generic_app import App, main

"""
See http://socorro.readthedocs.org/en/latest/databaseadminfunctions.html#we
ekly-report-partitions
See https://bugzilla.mozilla.org/show_bug.cgi?id=701253
"""


class WeeklyReportsPartitions(App):
    app_name = 'weekly_reports_partitions'
    app_version = '0.1'
    app_description = __doc__

    required_config = Namespace()
    required_config.add_option('transaction_executor_class',
                               default=TransactionExecutorWithInfiniteBackoff,
                               #default=TransactionExecutor,
                               doc='a class that will execute transactions')
    required_config.add_option('database_class',
                               default=ConnectionContext,
                               from_string_converter=class_converter
    )

    def run_query(self, connection):
        cursor = connection.cursor()
        cursor.execute('SELECT weekly_report_partitions()')

    def main(self):
        database = self.config.database_class(self.config)
        executor = self.config.transaction_executor_class(self.config,
                                                          database)
        executor(self.run_query)
        # alternative use could be like this:
        # with self.config.transaction_executor_class(self.config) as connection:
        #    self.run_query(connection)


if __name__ == '__main__':  # pragma: no cover
    main(WeeklyReportsPartitions)
