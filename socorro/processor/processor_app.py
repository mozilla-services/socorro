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

from socorro.app.fetch_transform_save_app import FetchTransformSaveApp
from socorro.external.postgresql.crashstorage import PostgreSQLCrashStorage
from socorro.external.crashstorage_base import PolyCrashStorage


#==============================================================================
class ProcessorApp(FetchTransformSaveApp):
    """the Socorro processor converts raw_crashes into processed_crashes"""
    app_name = 'processor_app'
    app_version = '3.0'
    app_description = __doc__

    FetchTransformSaveApp.required_config.source.crashstorage.default = \
        PostgreSQLCrashStorage
    FetchTransformSaveApp.required_config.destination.crashstorage.default = \
        PolyCrashStorage

    required_config = Namespace()
    required_config.add_option(
      'processor_class',
      doc='the class that transforms raw crashes into processed crashes',
      default='socorro.processor.legacy_processor',
      from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def transform(self, ooid):
        """"""
        raw_crash = self.source.get_raw_crash(ooid)
        dump = self.source.get_dump(ooid)
        if 'uuid' not in raw_crash:
            raw_crash.uuid = ooid
        processed_crash = \
          self.convert_raw_crash_to_processed_crash(
            raw_crash,
            dump
          )
        self.destination.save_processed(processed_crash)

    #--------------------------------------------------------------------------
    def _setup_source_and_destination(self):
        super(ProcessorApp, self)._setup_source_and_destination()
        self.processor = self.config.processor_class(config, self.quit_check)

