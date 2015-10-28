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

    #--------------------------------------------------------------------------
    @staticmethod
    def get_application_defaults():
        return {
            "source.crashstorage_class": FSDatedPermanentStorage,
            "destination.crashstorage_class": FSDatedPermanentStorage,
            "worker_task.worker_task_impl":
                "socorro.app.fts_worker_methods.ProcessorWorkerMethod",
        }

    #--------------------------------------------------------------------------
    def _setup_source_and_destination(self, transform_fn=None):
        """this method instantiates the 'processor.processor_class' which
        implements the transform method to be run by the workers to transform
        raw crashes into processed crashes.
        """
        if transform_fn is None:
            self.processor = self.config.processor.processor_class(
                self.config.processor,
                self.quit_check
            )
            transform_fn = self.processor.process_crash

        super(ProcessorApp, self)._setup_source_and_destination(
            transform_fn=transform_fn
        )

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

    #--------------------------------------------------------------------------
    def _cleanup(self):
        """when  the processor shutsdown, this function cleans up"""
        if self.companion_process:
            self.companion_process.close()
        self.config.logger.debug('telling processor to close')
        self.processor.close()
        self.config.logger.debug('processor done closing')


if __name__ == '__main__':
    main(ProcessorApp)

