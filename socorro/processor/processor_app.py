#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""the processor_app converts raw_crashes into processed_crashes"""

import collections
import logging
import os
import sys

from configman import Namespace
from configman.converters import class_converter
from configman.dotdict import DotDict
import six

from socorro.app.fetch_transform_save_app import FetchTransformSaveWithSeparateNewCrashSourceApp
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.lib import raven_client
from socorro.lib.util import dotdict_to_dict


# Defined separately for readability
CONFIG_DEFAULTS = {
    'always_ignore_mismatches': True,

    'source': {
        'benchmark_tag': 'BotoBenchmarkRead',
        'crashstorage_class': 'socorro.external.crashstorage_base.BenchmarkingCrashStorage',
        'wrapped_crashstore': 'socorro.external.boto.crashstorage.BotoS3CrashStorage',
    },

    'destination': {
        'crashstorage_class': 'socorro.external.crashstorage_base.PolyCrashStorage',

        # Each key in this list corresponds to a key in this dict containing
        # a crash storage config.
        'storage_namespaces': ','.join([
            's3',
            'elasticsearch',
            'statsd',
            'telemetry',
        ]),

        's3': {
            'active_list': 'save_raw_and_processed',
            'benchmark_tag': 'BotoBenchmarkWrite',
            'crashstorage_class': 'socorro.external.crashstorage_base.MetricsBenchmarkingWrapper',
            'metrics_prefix': 'processor.s3',
            'use_mapping_file': 'False',
            'wrapped_object_class': 'socorro.external.boto.crashstorage.BotoS3CrashStorage',
        },
        'elasticsearch': {
            'active_list': 'save_raw_and_processed',
            'benchmark_tag': 'BotoBenchmarkWrite',
            'crashstorage_class': 'socorro.external.crashstorage_base.MetricsBenchmarkingWrapper',
            'es_redactor': {
                'forbidden_keys': ', '.join([
                    'memory_report',
                    'upload_file_minidump_browser.json_dump',
                    'upload_file_minidump_flash1.json_dump',
                    'upload_file_minidump_flash2.json_dump',
                ]),
            },
            'metrics_prefix': 'processor.es',
            'use_mapping_file': 'False',
            'wrapped_object_class': (
                'socorro.external.es.crashstorage.ESCrashStorageRedactedJsonDump'
            ),
        },
        'statsd': {
            'active_list': 'save_raw_and_processed',
            'crashstorage_class': 'socorro.external.crashstorage_base.MetricsCounter',
            'metrics_prefix': 'processor',
        },
        'telemetry': {
            'active_list': 'save_raw_and_processed',
            'bucket_name': 'org-mozilla-telemetry-crashes',
            'crashstorage_class': 'socorro.external.crashstorage_base.MetricsBenchmarkingWrapper',
            'metrics_prefix': 'processor.telemetry',
            'wrapped_object_class': (
                'socorro.external.boto.crashstorage.TelemetryBotoS3CrashStorage'
            ),
        },
    },

    'companion_process': {
        'companion_class': 'socorro.processor.symbol_cache_manager.SymbolLRUCacheManager',
        'symbol_cache_size': '40G',
        'verbosity': 0,
    },

    'new_crash_source': {
        'crashstorage_class': 'socorro.external.rabbitmq.crashstorage.RabbitMQCrashStorage',
        'new_crash_source_class': (
            'socorro.external.rabbitmq.rmq_new_crash_source.RMQNewCrashSource'
        ),
    },

    'producer_consumer': {
        'maximum_queue_size': 8,
        'number_of_threads': 4,
    },

    'resource': {
        'boto': {
            'prefix': '',
            'boto_metrics_prefix': 'processor.s3'
        },

        'elasticsearch': {
            # FIXME(willkg): Where does this file come from?
            'elasticsearch_index_settings': (
                '/app/socorro/external/elasticsearch/socorro_index_settings.json'
            ),
            'timeout': 2,
            'use_mapping_file': False,
        },

        'rabbitmq': {
            'filter_on_legacy_processing': True,
            'routing_key': 'socorro.normal',
        },
    },
}


class ProcessorApp(FetchTransformSaveWithSeparateNewCrashSourceApp):
    """Configman app that generates processed_crashes from raw_crashes"""
    app_name = 'processor'
    app_version = '3.0'
    app_description = __doc__
    config_defaults = CONFIG_DEFAULTS

    required_config = Namespace()

    # Configuration is broken into three namespaces: processor,
    # new_crash_source, and companion_process

    # processor namespace
    #     This namespace is for config parameter having to do with the
    #     implementation of the algorithm of converting raw crashes into
    #     processed crashes. This algorithm can be swapped out for alternate
    #     algorithms.
    required_config.namespace('processor')
    required_config.processor.add_option(
        'processor_class',
        doc='the class that transforms raw crashes into processed crashes',
        default='socorro.processor.processor_2015.Processor2015',
        from_string_converter=class_converter
    )

    # companion_process namespace
    #     This namespace is for config parameters having to do with registering
    #     a companion process that runs alongside processor.
    required_config.namespace('companion_process')
    required_config.companion_process.add_option(
        'companion_class',
        doc='a classname that runs a process in parallel with the processor',
        default='',
        # default='socorro.processor.symbol_cache_manager.SymbolLRUCacheManager',
        from_string_converter=class_converter
    )

    required_config.namespace('sentry')
    required_config.sentry.add_option(
        'dsn',
        doc='DSN for Sentry via raven',
        default='',
        reference_value_from='secrets.sentry',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)

    def _capture_error(self, crash_id, exc_info):
        """Capture an error in sentry if able

        :arg crash_id: a crash id
        :arg exc_info: the exc info as it comes from sys.exc_info()

        """
        if self.config.sentry and self.config.sentry.dsn:
            sentry_dsn = self.config.sentry.dsn
        else:
            sentry_dsn = None

        raven_client.capture_error(
            sentry_dsn,
            self.logger,
            exc_info,
            extra={'crash_id': crash_id}
        )

    def _transform(self, crash_id):
        """Transform a raw crash into a process crash

        The ``crash_id`` passed in is used as a key to fetch the raw crash data
        from the ``source``, the ``processor_class`` processes the crash and
        the processed crash is saved to the ``destination``.

        """
        # Fetch the raw crash data
        try:
            raw_crash = self.source.get_raw_crash(crash_id)
            dumps = self.source.get_raw_dumps_as_files(crash_id)
        except CrashIDNotFound:
            # If the crash isn't found, we just reject it--no need to capture
            # errors here
            self.processor.reject_raw_crash(crash_id, 'crash cannot be found in raw crash storage')
            return
        except Exception as x:
            # We don't know what this error is, so we should capture it
            self._capture_error(crash_id, sys.exc_info())
            self.logger.warning('error loading crash %s', crash_id, exc_info=True)
            self.processor.reject_raw_crash(crash_id, 'error in loading: %s' % x)
            return

        # Fetch processed crash data--there won't be any if this crash hasn't
        # been processed, yet
        try:
            processed_crash = self.source.get_unredacted_processed(crash_id)
        except CrashIDNotFound:
            processed_crash = DotDict()

        # Process the crash and remove any temporary artifacts from disk
        try:
            # Process the crash to generate a processed crash
            processed_crash = self.processor.process_crash(raw_crash, dumps, processed_crash)

            # Convert the raw and processed crashes from DotDict into Python standard data
            # structures
            raw_crash = dotdict_to_dict(raw_crash)
            processed_crash = dotdict_to_dict(processed_crash)

            # bug 866973 - save_raw_and_processed() instead of just save_processed().
            # The raw crash may have been modified by the processor rules. The
            # individual crash storage implementations may choose to honor re-saving
            # the raw_crash or not.

            self.destination.save_raw_and_processed(raw_crash, None, processed_crash, crash_id)
            self.logger.info('saved - %s', crash_id)
        except Exception:
            # Capture the exception so we don't lose it as we do other things
            exc_type, exc_value, exc_tb = sys.exc_info()

            # PolyStorage can throw a PolyStorageException which is a sequence
            # of exc_info items, so we need to capture each one
            if isinstance(exc_value, collections.Sequence):
                exc_info = exc_value
            else:
                exc_info = [(exc_type, exc_value, exc_tb)]

            for exc_info_item in exc_info:
                self._capture_error(crash_id, exc_info_item)
                self.logger.warning('error in processing or saving crash %s', crash_id)

            # Re-raise the original exception with the correct traceback
            six.reraise(exc_type, exc_value, exc_tb)

        finally:
            # Clean up any dump files saved to the file system
            for a_dump_pathname in dumps.values():
                if 'TEMPORARY' in a_dump_pathname:
                    try:
                        os.unlink(a_dump_pathname)
                    except OSError as x:
                        self.logger.info('deletion of dump failed: %s', x)

    def _setup_source_and_destination(self):
        """Instantiates classes necessary for processing"""
        super(ProcessorApp, self)._setup_source_and_destination()
        if self.config.companion_process.companion_class:
            self.companion_process = self.config.companion_process.companion_class(
                self.config.companion_process,
                self.quit_check
            )
        else:
            self.companion_process = None

        self.config.processor_name = self.app_instance_name

        # This function will be called by the MainThread periodically
        # while the threaded_task_manager processes crashes.
        self.waiting_func = None

        self.processor = self.config.processor.processor_class(
            self.config.processor,
            quit_check_callback=self.quit_check
        )

    def close(self):
        """Cleans up the processor on shutdown"""
        super(ProcessorApp, self).close()
        try:
            self.companion_process.close()
        except AttributeError:
            # There is either no companion or it doesn't have a close method
            # we can skip on
            pass
        try:
            self.processor.close()
        except AttributeError:
            # The processor implementation does not have a close method
            # we can blithely skip on
            pass


if __name__ == '__main__':
    sys.exit(ProcessorApp.run())
