#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""this app will move crashes from one storage location to another"""

from configman import Namespace, class_converter

from socorro.app.fetch_transform_save_app import FetchTransformSaveApp, main


#==============================================================================
class CrashMoverApp(FetchTransformSaveApp):
    app_name = 'crashmover'
    app_version = '2.0'
    app_description = __doc__

    required_config = Namespace()


#==============================================================================
class ProcessedCrashCopierApp(FetchTransformSaveApp):
    app_name = 'processed_crashmover'
    app_version = '1.0'
    app_description = __doc__

    required_config = Namespace()
    #--------------------------------------------------------------------------
    # new_crash_source namespace
    #     this namespace is for config parameter having to do with the source
    #     of new crash_ids.
    #--------------------------------------------------------------------------
    required_config.namespace('new_crash_source')
    required_config.new_crash_source.add_option(
      'new_crash_source_class',
      doc='an iterable that will stream crash_ids needing copying',
      default='socorro.processor.timemachine.PGQueryNewCrashSource',
      from_string_converter=class_converter
    )

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
                'socorro.processor.timemachine.PGQueryNewCrashSource'
        }

    #--------------------------------------------------------------------------
    def source_iterator(self):
        """this iterator yields individual crash_ids from the source
        crashstorage class's 'new_crash_ids' method."""
        self.iterator = self.config.new_crash_source.new_crash_source_class(
          self.config.new_crash_source,
          'not-a-processor',
          self.quit_check
        )
        for x in self.iterator():
            self.config.logger.debug('yielding %s', x)
            yield x  # (args, kwargs) or None

    #--------------------------------------------------------------------------
    def transform(self, crash_id):
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

if __name__ == '__main__':
    main(CrashMoverApp)
