#!/usr/bin/env python

import os
import logging
logger = logging.getLogger("weeklyReportsPartitions")

from configman import Namespace, ConfigurationManager
import socorro
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

    required_config = Namespace()
    required_config.add_option('wilma', default='Wilma')
    required_config.add_option('transaction_executor_class',
                                 default=TransactionExecutorWithBackoff,
                                 doc='a class that will execute transactions')

    def run_query(self, connection):
        connection.query('select * from pg_class')
        #connection.query('SELECT weekly_report_partitions();')

    def main(self):
        #print self.config
        #print self.config.keys()
        executor = self.config.transaction_executor_class(self.config)
        executor.do_transaction(self.run_query)
        #return 
        #with self.context() as config:
        #    # the configuration has a class that can execute transactions
        #    # we instantiate it here.
        #    executor = config.transaction_executor_class(config)
        #    executor.do_transaction(run_query)

if __name__ == '__main__':
    main(WeeklyReportsPartitions)
