#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""this app will move crashes from one storage location to another"""

from configman import Namespace

from socorrolib.app.fetch_transform_save_app import (
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
                'socorrolib.lib.task_manager.TaskManager',
            'producer_consumer.quit_on_empty_queue': True,
            'new_crash_source.new_crash_source_class':
                'socorro.processor.timemachine.PGQueryNewCrashSource'
        }

    #--------------------------------------------------------------------------
    def _transform(self, crash_id):
        """this default transform function only transfers raw data from the
        source to the destination without changing the data.  While this may
        be good enough for the raw crashmover, the processor would override
        this method to create and save processed crashes"""
        self.config.logger.debug('trying %s', crash_id)
        try:
            self.config.logger.debug('get_unredacted_processed')
            processed_crash = self.source.get_unredacted_processed(crash_id)
        except Exception as x:
            self.config.logger.error(
                "reading processed_crash: %s",
                str(x),
                exc_info=True
            )
            processed_crash = {}
        try:
            self.config.logger.debug('save_processed')
            self.destination.save_processed(processed_crash)
        except Exception as x:
            self.config.logger.error(
                "writing processed_crash: %s",
                str(x),
                exc_info=True
            )


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
        }

    #--------------------------------------------------------------------------
    def _transform(self, crash_id):
        """this implementation is the framework on how a raw crash is
        converted into a processed crash.  The 'crash_id' passed in is used as
        a key to fetch the raw crash from the 'source', the conversion funtion
        implemented by the 'processor_class' is applied, the
        processed crash is saved to the 'destination', and then 'finished_func'
        is called."""
        try:
            raw_crash = self.source.get_raw_crash(crash_id)
            processed_crash = self.source.get_processed(
                crash_id
            )
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

        if 'uuid' not in raw_crash:
            raw_crash.uuid = crash_id
        self.destination.save_raw_and_processed(
            raw_crash,
            None,
            processed_crash,
            crash_id
        )
        self.config.logger.info('saved - %s', crash_id)

if __name__ == '__main__':
    main(CrashMoverApp)
