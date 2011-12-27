#!/usr/bin/python

import os
import logging
logger = logging.getLogger("weeklyReportsPartitions")

from configman import Namespace, ConfigurationManager
from socorro.database.transaction_executor import TransactionExecutorWithBackoff

"""
See http://socorro.readthedocs.org/en/latest/databaseadminfunctions.html#weekly-report-partitions
See https://bugzilla.mozilla.org/show_bug.cgi?id=701253
"""

def run_query(connection):
    connection.query('SELECT weekly_report_partitions();')


def run(config):
    definition_source = Namespace()
    definition_source.add_option('transaction_executor_class',
                                 default=TransactionExecutorWithBackoff,
                                 doc='a class that will execute transactions')

    app_name = os.path.splitext(os.path.basename(__file__))[0]
    c = ConfigurationManager(definition_source,
                             app_name=app_name,
                             app_description=__doc__)

    with c.context() as config:
        # the configuration has a class that can execute transactions
        # we instantiate it here.
        executor = config.transaction_executor_class(config)
        executor.do_transaction(run_query)
