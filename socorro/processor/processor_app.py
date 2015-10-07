#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""the processor_app converts raw_crashes into processed_crashes"""

import os

from configman import Namespace
from configman.converters import class_converter

from socorro.app.fetch_transform_save_app import (
    FetchTransformSaveWithSeparateNewCrashSourceApp,
    main
)
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.lib.util import DotDict
from socorro.external.fs.crashstorage import FSDatedPermanentStorage


#==============================================================================
class ProcessorApp(FetchTransformSaveWithSeparateNewCrashSourceApp):
    """the Socorro processor converts raw_crashes into processed_crashes"""
    app_name = 'processor'
    app_version = '3.0'
    app_description = __doc__

    required_config = Namespace()
    # configuration is broken into three namespaces: processor,
    # new_crash_source, and companion_process
    #--------------------------------------------------------------------------
    # processor namespace
    #     this namespace is for config parameter having to do with the
    #     implementation of the algorithm of converting raw crashes into
    #     processed crashes.  This algorithm can be swapped out for alternate
    #     algorithms.
    #--------------------------------------------------------------------------
    required_config.namespace('processor')
    required_config.processor.add_option(
        'processor_class',
        doc='the class that transforms raw crashes into processed crashes',
        default='socorro.processor.socorrolite_processor_2015'
        '.SocorroLiteProcessorAlgorithm2015',
        from_string_converter=class_converter
    )
    #--------------------------------------------------------------------------
    # companion_process namespace
    #     this namespace is for config parameters having to do with registering
    #     a companion process that runs alongside processor
    #--------------------------------------------------------------------------
    required_config.namespace('companion_process')
    required_config.companion_process.add_option(
        'companion_class',
        doc='a classname that runs a process in parallel with the processor',
        default='',
        #default='socorro.processor.symbol_cache_manager.SymbolLRUCacheManager',
        from_string_converter=class_converter
    )

    ###########################################################################
    ### TODO: implement an __init__ and a waiting func.  The waiting func
    ### will take registrations of periodic things to do over some time
    ### interval.  the first periodic thing is the rereading of the
    ### signature generation stuff from the database.
    ###########################################################################

    #--------------------------------------------------------------------------
    @staticmethod
    def get_application_defaults():
        return {
            "source.crashstorage_class": FSDatedPermanentStorage,
            "destination.crashstorage_class": FSDatedPermanentStorage,
        }

    #--------------------------------------------------------------------------
    def quit_check(self):
        """the quit polling function.  This method, used as a callback, will
        propagate to any thread that loops."""
        self.task_manager.quit_check()

    #--------------------------------------------------------------------------
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
            self.processor.reject_raw_crash(
                crash_id,
                'this crash cannot be found in raw crash storage'
            )
            return
        except Exception, x:
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
        finally:
            # earlier, we created the dumps as files on the file system,
            # we need to clean up after ourselves.
            for a_dump_pathname in dumps.itervalues():
                try:
                    if "TEMPORARY" in a_dump_pathname:
                        os.unlink(a_dump_pathname)
                except OSError, x:
                    # the file does not actually exist
                    self.config.logger.info(
                        'deletion of dump failed: %s',
                        x,
                    )

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
    def _cleanup(self):
        """when  the processor shutsdown, this function cleans up"""
        if self.companion_process:
            self.companion_process.close()
        self.iterator.close()


if __name__ == '__main__':
    main(ProcessorApp)

