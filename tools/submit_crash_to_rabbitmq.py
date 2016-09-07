#!/usr/bin/env python

"""
Script to put crash IDs into RabbitMQ from the command line.
This is useful when you have a local processor running without a
collector or crashmover.

To run it, pass one more more crash IDs like this::


    $ ./tools/submit_crash_to_rabbitmq.py e9a624b0-fbcc-4e95-a0a8-d2a152160907

"""

import logging

from configman import configuration, Namespace
from socorrolib.lib.util import DotDict
from socorrolib.lib.converters import change_default
from socorro.external.rabbitmq.connection_context import ConnectionContext
from socorro.external.rabbitmq.crashstorage import RabbitMQCrashStorage
from socorro.database.transaction_executor import TransactionExecutor

logger = logging.getLogger(__file__)


class SingleCrashMQCrashStorage(RabbitMQCrashStorage):
    required_config = Namespace()
    required_config.routing_key = change_default(
        RabbitMQCrashStorage,
        'routing_key',
        'socorro.normal'
    )
    required_config.rabbitmq_class = change_default(
        RabbitMQCrashStorage,
        'rabbitmq_class',
        ConnectionContext,
    )
    required_config.transaction_executor_class = change_default(
        RabbitMQCrashStorage,
        'transaction_executor_class',
        TransactionExecutor
    )

    def submit(self, crash_ids):
        if not isinstance(crash_ids, (list, tuple)):
            crash_ids = [crash_ids]
        success = bool(crash_ids)
        for crash_id in crash_ids:
            if not self.save_raw_crash(
                DotDict({'legacy_processing': 0}),
                [],
                crash_id
            ):
                success = False
        return success


def run(*crash_ids):

    definition_source = Namespace()
    definition_source.namespace('queuing')
    definition_source.queuing.add_option(
        'rabbitmq_reprocessing_class',
        default=SingleCrashMQCrashStorage,
    )
    config_dict = {
        'resource': {
            'rabbitmq': {
                'host': 'localhost',
                'port': '5672',
                'virtual_host': '/'
            }
        },
        'secrets': {
            'rabbitmq': {
                'rabbitmq_password': 'guest',
                'rabbitmq_user': 'guest'
            }
        }
    }
    config = configuration(
        definition_source=definition_source,
        values_source_list=[config_dict],
    )
    config.queuing.logger = logger
    config.logger = logger
    storage = SingleCrashMQCrashStorage(config=config['queuing'])
    for crash_id in crash_ids:
        print storage.submit(crash_id)
    return 0


if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    sys.exit(run(*args))
