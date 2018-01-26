#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""the processor_app converts raw_crashes into processed_crashes"""

import os
import sys
import collections

from configman import Namespace
from configman.converters import class_converter

from socorro.app.fetch_transform_save_app import FetchTransformSaveWithSeparateNewCrashSourceApp
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.lib.util import DotDict
from socorro.lib import raven_client
from socorro.external.fs.crashstorage import FSDatedPermanentStorage


class ProcessorApp(FetchTransformSaveWithSeparateNewCrashSourceApp):
    """the Socorro processor converts raw_crashes into processed_crashes"""
    app_name = 'processor'
    app_version = '3.0'
    app_description = __doc__
    config_module = 'socorro.processor.config'

    required_config = Namespace()
    # configuration is broken into three namespaces: processor,
    # new_crash_source, and companion_process

    # processor namespace
    #     this namespace is for config parameter having to do with the
    #     implementation of the algorithm of converting raw crashes into
    #     processed crashes.  This algorithm can be swapped out for alternate
    #     algorithms.
    required_config.namespace('processor')
    required_config.processor.add_option(
        'processor_class',
        doc='the class that transforms raw crashes into processed crashes',
        default='socorro.processor.processor_2015.Processor2015',
        from_string_converter=class_converter
    )

    # companion_process namespace
    #     this namespace is for config parameters having to do with registering
    #     a companion process that runs alongside processor
    required_config.namespace('companion_process')
    required_config.companion_process.add_option(
        'companion_class',
        doc='a classname that runs a process in parallel with the processor',
        default='',
        # default='socorro.processor.symbol_cache_manager.SymbolLRUCacheManager',
        from_string_converter=class_converter
    )

    ###########################################################################
    # TODO: implement an __init__ and a waiting func.  The waiting func
    # will take registrations of periodic things to do over some time
    # interval.  the first periodic thing is the rereading of the
    # signature generation stuff from the database.
    ###########################################################################

    required_config.namespace('sentry')
    required_config.sentry.add_option(
        'dsn',
        doc='DSN for Sentry via raven',
        default='',
        reference_value_from='secrets.sentry',
    )

    @staticmethod
    def get_application_defaults():
        return {
            "source.crashstorage_class": FSDatedPermanentStorage,
            "destination.crashstorage_class": FSDatedPermanentStorage,
        }

    def _capture_error(self, crash_id, exc_type, exc_value, exc_tb):
        """Capture an error in sentry if able

        The `exc_*` arguments come from calling `sys.exc_info`.

        :arg crash_id: a crash id
        :arg exc_type: the exc class
        :arg exc_value: the exception
        :arg exc_tb: the traceback for the exception

        """

        if self.config.sentry and self.config.sentry.dsn:
            try:
                if isinstance(exc_value, collections.Sequence):
                    # Then it's already an iterable!
                    exceptions = exc_value
                else:
                    exceptions = [exc_value]
                client = raven_client.get_client(self.config.sentry.dsn)
                client.context.activate()
                client.context.merge({'extra': {
                    'crash_id': crash_id,
                }})
                try:
                    for exception in exceptions:
                        identifier = client.captureException(exception)
                        self.config.logger.info(
                            'Error captured in Sentry! Reference: {}'.format(identifier)
                        )
                finally:
                    client.context.clear()
            except Exception:
                self.config.logger.error('Unable to report error with Raven', exc_info=True)
        else:
            self.config.logger.warning('Sentry DSN is not configured and an exception happened')

    def _transform(self, crash_id):
        """this implementation is the framework on how a raw crash is
        converted into a processed crash.  The 'crash_id' passed in is used as
        a key to fetch the raw crash from the 'source', the conversion funtion
        implemented by the 'processor_class' is applied, the
        processed crash is saved to the 'destination'"""
        try:
            raw_crash = self.source.get_raw_crash(crash_id)
            dumps = self.source.get_raw_dumps_as_files(crash_id)
        except CrashIDNotFound:
            # If the crash isn't found, we just reject it--no need to capture
            # errors here
            self.processor.reject_raw_crash(
                crash_id,
                'this crash cannot be found in raw crash storage'
            )
            return
        except Exception as x:
            # We don't know what this error is, so we should capture it
            exc_type, exc_value, exc_tb = sys.exc_info()
            self._capture_error(crash_id, exc_type, exc_value, exc_tb)

            self.config.logger.warning(
                'error loading crash %s',
                crash_id,
                exc_info=True
            )
            self.processor.reject_raw_crash(
                crash_id,
                'error in loading: %s' % x
            )
            return

        try:
            processed_crash = self.source.get_unredacted_processed(
                crash_id
            )
        except CrashIDNotFound:
            processed_crash = DotDict()

        try:
            if 'uuid' not in raw_crash:
                raw_crash.uuid = crash_id
            processed_crash = (
                self.processor.process_crash(
                    raw_crash,
                    dumps,
                    processed_crash,
                )
            )
            """ bug 866973 - save_raw_and_processed() instead of just
                save_processed().  The raw crash may have been modified
                by the processor rules.  The individual crash storage
                implementations may choose to honor re-saving the raw_crash
                or not.
            """
            self.destination.save_raw_and_processed(
                raw_crash,
                None,
                processed_crash,
                crash_id
            )
            self.config.logger.info('saved - %s', crash_id)
        except Exception:
            # Immediately capture this as local variables.
            # During this error handling we're going to be using other
            # try:except: constructs (e.g. swallowing raven send errors)
            # so we can't reference `sys.exc_info()` later.
            exc_type, exc_value, exc_tb = sys.exc_info()

            # Capture the error
            self._capture_error(crash_id, exc_type, exc_value, exc_tb)

            # Why not just do `raise exception`?
            # Because if we don't do it this way, the eventual traceback
            # is going to point to *this* line (right after this comment)
            # rather than the actual error where it originally happened.
            raise exc_type, exc_value, exc_tb
        finally:
            # earlier, we created the dumps as files on the file system,
            # we need to clean up after ourselves.
            for a_dump_pathname in dumps.itervalues():
                try:
                    if "TEMPORARY" in a_dump_pathname:
                        os.unlink(a_dump_pathname)
                except OSError as x:
                    # the file does not actually exist
                    self.config.logger.info(
                        'deletion of dump failed: %s',
                        x,
                    )

    def _setup_source_and_destination(self):
        """this method simply instatiates the source, destination,
        new_crash_source, and the processor algorithm implementation."""
        super(ProcessorApp, self)._setup_source_and_destination()
        if self.config.companion_process.companion_class:
            self.companion_process = \
                self.config.companion_process.companion_class(
                    self.config.companion_process,
                    self.quit_check
                )
        else:
            self.companion_process = None

        self.config.processor_name = self.app_instance_name

        # this function will be called by the MainThread periodically
        # while the threaded_task_manager processes crashes.
        self.waiting_func = None

        self.processor = self.config.processor.processor_class(
            self.config.processor,
            self.quit_check
        )

    def close(self):
        """when  the processor shutsdown, this function cleans up"""
        try:
            self.companion_process.close()
        except AttributeError:
            # there is either no companion or it doesn't have a close method
            # we can skip on
            pass
        try:
            self.processor.close()
        except AttributeError:
            # the processor implementation does not have a close method
            # we can blithely skip on
            pass


if __name__ == '__main__':
    sys.exit(ProcessorApp.run())
