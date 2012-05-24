"""this is the basis for any app that follows the fetch/transform/save model

* the configman versions of the crash mover and the processor apps will
  derive from this class

The form of fetch/transform/save, of course, in three parts
1) fetch - some iterating or streaming function or object fetches packets of
           from data a source
2) transform - some function transforms each packet of data into a new form
3) save - some function or class saves or streams the packet to some data
           sink.

For the crash mover, the fetch phase is reading new crashes from the
collector's file system datastore.  The transform phase is the degenerate
case of identity: no transformation.  The save phase is just sending the
crashes to HBase.

For the processor, the fetch phase is reading from the new crash queue.  In,
2012, that's the union of reading a postgres jobs/ooid table and fetching the
crash from HBase.  The transform phase is the running of minidump stackwalk
and production of the processed crash data.  The save phase is the union of
sending new crash records to Postgres; sending the processed crash to HBase;
the the submission of the ooid to Elastic Search."""

import copy

from configman import Namespace
from configman.converters import class_converter

from socorro.app.fetch_transform_save_app import FetchTransformSaveApp, main
from socorro.external.postgresql.crashstorage import PostgreSQLCrashStorage
from socorro.external.crashstorage_base import PolyCrashStorage


#==============================================================================
class ProcessorApp(FetchTransformSaveApp):
    """the Socorro processor converts raw_crashes into processed_crashes"""
    app_name = 'processor_app'
    app_version = '3.0'
    app_description = __doc__

    # set the Option defaults in the parent class
    FetchTransformSaveApp.required_config.source.crashstorage.set_default(
      PostgreSQLCrashStorage
    )
    FetchTransformSaveApp.required_config.destination.crashstorage.set_default(
      PolyCrashStorage
    )

    required_config = Namespace()
    required_config.namespace('processor')
    required_config.processor.add_option(
      'processor_class',
      doc='the class that transforms raw crashes into processed crashes',
      default='socorro.processor.legacy_processor.LegacyCrashProcessor',
      from_string_converter=class_converter
    )
    required_config.namespace('ooid_source')
    required_config.ooid_source.add_option(
      'ooid_source_class',
      doc='an iterable that will stream ooids needing processing',
      default='socorro.processor.legacy_ooid_source.LegacyOoidSource',
      from_string_converter=class_converter
    )
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
        """this iterator yields individual ooids from the source crashstorage
        class's 'new_ooids' method."""
        self.iterator = self.config.ooid_source.ooid_source_class(
          self.config.ooid_source,
          self.registrar.processor_name,
          self.quit_check
        )
        while(True):  # loop forever and never raise StopIteration
            for x in self.iterator():
                self.registrar.checkin()
                if x is None:
                    yield None
                else:
                    yield ((x,), {})  # (args, kwargs)
            else:
                yield None  # if the inner iterator yielded nothing at all,
                            # yield None to give the caller the chance to sleep

    #--------------------------------------------------------------------------
    def quit_check(self):
        self.task_manager.quit_check()

    #--------------------------------------------------------------------------
    def transform(self, ooid):
        """"""
        raw_crash = self.source.get_raw_crash(ooid)
        dump = self.source.get_raw_dump(ooid)
        if 'uuid' not in raw_crash:
            raw_crash.uuid = ooid
        processed_crash = \
          self.processor.convert_raw_crash_to_processed_crash(
            raw_crash,
            dump
          )
        self.destination.save_processed(processed_crash)

    #--------------------------------------------------------------------------
    def _setup_source_and_destination(self):
        super(ProcessorApp, self)._setup_source_and_destination()
        self.registrar = self.config.registrar.registrar_class(
          self.config.registrar,
          self.quit_check
        )
        self.processor = self.config.processor.processor_class(
          self.config.processor,
          self.quit_check
        )

    #--------------------------------------------------------------------------
    def _cleanup(self):
        self.registrar.unregister()
        self.iterator.close()

if __name__ == '__main__':
    main(ProcessorApp)