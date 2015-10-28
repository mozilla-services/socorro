#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""this app will move crashes from one storage location to another"""

from configman import Namespace

from socorro.app.fetch_transform_save_app import (
    FetchTransformSaveApp,
    FetchTransformSaveWithSeparateNewCrashSourceApp,
    main
)
from socorro.external.crashstorage_base import (
    CrashIDNotFound,
)


#==============================================================================
class CrashMoverApp(FetchTransformSaveApp):
    app_name = 'crashmover'
    app_version = '2.0'
    app_description = __doc__

    required_config = Namespace()


#==============================================================================
class ProcessedCrashCopierApp(FetchTransformSaveWithSeparateNewCrashSourceApp):
    app_name = 'processed_crash_copier'
    app_version = '1.0'
    app_description = __doc__

    required_config = Namespace()

    #--------------------------------------------------------------------------
    @staticmethod
    def get_application_defaults():
        """this method allows an app to inject defaults into the configuration
        that can override defaults not under the direct control of the app.
        For example, if an app were to use a class that had a config default
        of X and that was not appropriate as a default for this app, then
        this method could be used to override that default.

        This is a technique of getting defaults into an app that replaces
        an older method of going to the configman option and using the
        'set_default' method with 'force=True'"""

        return {
            'source.crashstorage_class':
                'socorro.external.boto.crashstorage.BotoS3CrashStorage',
            'destination.crashstorage_class':
                'socorro.external.fs.crashstorage.TarFileCrashStore',
            'producer_consumer.producer_consumer_class':
                'socorro.lib.task_manager.TaskManager',
            'producer_consumer.quit_on_empty_queue': True,
            'new_crash_source.new_crash_source_class':
                'socorro.processor.timemachine.PGQueryNewCrashSource',
            "worker_task.worker_task_impl":
                "socorro.app.fts_worker_methods.ProcessedCrashCopyWorkerMethod",
        }


#==============================================================================
class RawAndProcessedCopierApp(FetchTransformSaveWithSeparateNewCrashSourceApp):
    """copy raw & processed crashes from a source to a destination"""
    app_name = 'raw_and_processed_crash_copier'
    app_version = '1.0'
    app_description = __doc__

    #--------------------------------------------------------------------------
    @staticmethod
    def get_application_defaults():
        return {
            'source.crashstorage_class':
                'socorro.external.boto.crashstorage.BotoS3CrashStorage',
            "destination.crashstorage_class":
                'socorro.external.es.crashstorage.'
                'ESCrashStorageNoStackwalkerOutput',
            "worker_task.worker_task_impl":
                "socorro.app.fts_worker_methods.ProcessorWorkerMethod",
        }


if __name__ == '__main__':
    main(CrashMoverApp)
