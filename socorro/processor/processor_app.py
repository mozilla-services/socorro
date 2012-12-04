#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""the processor_app converts raw_crashes into processed_crashes"""

from configman import Namespace
from configman.converters import class_converter

from socorro.app.fetch_transform_save_app import FetchTransformSaveApp, main
from socorro.external.filesystem.crashstorage import FileSystemRawCrashStorage
from socorro.external.crashstorage_base import (
  PolyCrashStorage,
  CrashIDNotFound,
)


#==============================================================================
class ProcessorApp(FetchTransformSaveApp):
    """the Socorro processor converts raw_crashes into processed_crashes"""
    app_name = 'processor'
    app_version = '3.0'
    app_description = __doc__

    # set the Option defaults in the parent class to values that make sense
    # for the context of this app
    FetchTransformSaveApp.required_config.source.crashstorage_class \
      .set_default(
      FileSystemRawCrashStorage
    )
    FetchTransformSaveApp.required_config.destination.crashstorage_class \
      .set_default(
      PolyCrashStorage
    )

    required_config = Namespace()
    # configuration is broken into three namespaces: processor,
    # new_crash_source, and registrar
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
      default='socorro.processor.legacy_processor.LegacyCrashProcessor',
      from_string_converter=class_converter
    )
    #--------------------------------------------------------------------------
    # new_crash_source namespace
    #     this namespace is for config parameter having to do with the source
    #     of new crash_ids.
    #--------------------------------------------------------------------------
    required_config.namespace('new_crash_source')
    required_config.new_crash_source.add_option(
      'new_crash_source_class',
      doc='an iterable that will stream crash_ids needing processing',
      default='socorro.processor.legacy_new_crash_source.LegacyNewCrashSource',
      from_string_converter=class_converter
    )
    #--------------------------------------------------------------------------
    # registrar namespace
    #     this namespace is for config parameters having to do with registering
    #     the processor so that the monitor is aware of it.
    #--------------------------------------------------------------------------
    required_config.namespace('registrar')
    required_config.registrar.add_option(
      'registrar_class',
      doc='the class that registers and tracks processors',
      default='socorro.processor.registration_client.'
              'ProcessorAppRegistrationClient',
      from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def source_iterator(self):
        """this iterator yields individual crash_ids from the source
        crashstorage class's 'new_crash_ids' method."""
        self.iterator = self.config.new_crash_source.new_crash_source_class(
          self.config.new_crash_source,
          self.registrar.processor_name,
          self.quit_check
        )
        while True:  # loop forever and never raise StopIteration
            for x in self.iterator():
                if x is None:
                    yield None
                else:
                    yield ((x,), {})  # (args, kwargs)
            else:
                yield None  # if the inner iterator yielded nothing at all,
                            # yield None to give the caller the chance to sleep

    #--------------------------------------------------------------------------
    def quit_check(self):
        """the quit polling function.  This method, used as a callback, will
        propagate to any thread that loops."""
        self.task_manager.quit_check()

    #--------------------------------------------------------------------------
    def transform(self, crash_id):
        """this implementation is the framework on how a raw crash is
        converted into a processed crash.  The 'crash_id' passed in is used as
        a key to fetch the raw crash from the 'source', the conversion funtion
        implemented by the 'processor_class' is applied, and then the
        processed crash is saved to the 'destination'."""
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
            self.config.logger.warning('error loading crash %s',
                                       crash_id,
                                       exc_info=True)
            self.processor.reject_raw_crash(
              crash_id,
              'error in loading: %s' % x
            )
            return

        if 'uuid' not in raw_crash:
            raw_crash.uuid = crash_id
        processed_crash = \
          self.processor.convert_raw_crash_to_processed_crash(
            raw_crash,
            dumps
          )
        self.destination.save_processed(processed_crash)

    #--------------------------------------------------------------------------
    def _setup_source_and_destination(self):
        """this method simply instatiates the source, destination,
        new_crash_source, and the processor algorithm implementation."""
        super(ProcessorApp, self)._setup_source_and_destination()
        self.registrar = self.config.registrar.registrar_class(
          self.config.registrar,
          self.quit_check
        )
        self.config.processor_name = "%s:2012" % self.registrar.processor_name
        # this function will be called by the MainThread periodically
        # while the threaded_task_manager processes crashes.
        self.waiting_func = self.registrar.checkin

        self.processor = self.config.processor.processor_class(
          self.config.processor,
          self.quit_check
        )

    #--------------------------------------------------------------------------
    def _cleanup(self):
        """when  the processor shutsdown, this function cleans up"""
        self.registrar.unregister()
        self.iterator.close()


if __name__ == '__main__':
    main(ProcessorApp)
