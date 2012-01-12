#!/usr/bin/python

import os
import logging
logger = logging.getLogger("weeklyReportsPartitions")

from configman import Namespace, ConfigurationManager
from socorro.database.transaction_executor import TransactionExecutorWithBackoff
from socorro.app.generic_app import App, main

"""
See http://socorro.readthedocs.org/en/latest/databaseadminfunctions.html#weekly-report-partitions
See https://bugzilla.mozilla.org/show_bug.cgi?id=701253
"""


class WeeklyReportsPartitions(App):
    app_name = 'weekly_reports_partitions'
    app_version = '0.1'
    app_description = __doc__

    definition_source = Namespace()
    definition_source.add_option('transaction_executor_class',
                                 default=TransactionExecutorWithBackoff,
                                 doc='a class that will execute transactions')

    def run_query(self, connection):
        connection.query('SELECT weekly_report_partitions();')

    def main(self):
        with self.config.context() as config:
            # the configuration has a class that can execute transactions
            # we instantiate it here.
            executor = config.transaction_executor_class(config)
            executor.do_transaction(run_query)
