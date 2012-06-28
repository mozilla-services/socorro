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

import signal

from configman import Namespace
from configman.converters import class_converter

from socorro.lib.threaded_task_manager import ThreadedTaskManager, \
                                              respond_to_SIGTERM
from socorro.app.generic_app import App, main


#==============================================================================
class FetchTransformSaveApp(App):
    """base class for apps that follow the fetch/transform/save model"""
    app_name = 'generic_fetch_transform_save_app'
    app_version = '0.1'
    app_description = __doc__

    required_config = Namespace()
    # the required config is broken into two parts: the source and the
    # destination.  Each of those gets assigned a crasnstorage class.
    required_config.source = Namespace()
    # For source, the storage class should be one that defines a method
    # of fetching new crashes through the three storage api methods: the
    # iterator 'new_ooids' and the accessors 'get_raw_crash' and 'get_dump'
    required_config.source.add_option(
      'crashstorage',
      doc='the source storage class',
      default=None,
      from_string_converter=class_converter
    )
    required_config.destination = Namespace()
    # For destination, the storage class should implement the 'save_raw_crash'
    # method.  Of course, a subclass may redefine either the source_iterator
    # or transform methods and therefore completely redefine what api calls
    # are relevant.
    required_config.destination.add_option(
      'crashstorage',
      doc='the destination storage class',
      default=None,
      from_string_converter=class_converter
    )
    required_config.producer_consumer = Namespace()
    required_config.producer_consumer.add_option(
      'producer_consumer_class',
      doc='the class implements a threaded producer consumer queue',
      default='socorro.lib.threaded_task_manager.ThreadedTaskManager',
      from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(FetchTransformSaveApp, self).__init__(config)
        self.waiting_func = None

    #--------------------------------------------------------------------------
    def source_iterator(self):
        """this iterator yields individual ooids from the source crashstorage
        class's 'new_ooids' method."""
        while(True):  # loop forever and never raise StopIteration
            for x in self.source.new_crashes():
                if x is None:
                    yield None
                else:
                    yield ((x,), {})  # (args, kwargs)
            else:
                yield None  # if the inner iterator yielded nothing at all,
                            # yield None to give the caller the chance to sleep

    #--------------------------------------------------------------------------
    def transform(self, ooid):
        """this default transform function only transfers raw data from the
        source to the destination without changing the data.  While this may
        be good enough for the raw crashmover, the processor would override
        this method to create and save processed crashes"""
        raw_crash = self.source.get_raw_crash(ooid)
        dump = self.source.get_dump(ooid)
        self.destination.save_raw_crash(raw_crash, dump)

    #--------------------------------------------------------------------------
    def quit_check(self):
        self.task_manager.quit_check()

    #--------------------------------------------------------------------------
    def signal_quit(self):
        self.task_manager.stop()

    #--------------------------------------------------------------------------
    def _setup_source_and_destination(self):
        """instantiate the classes that implement the source and destination
        crash storage systems."""
        try:
            self.source = self.config.source.crashstorage(
              self.config.source,
              quit_check_callback=self.quit_check
            )
        except Exception:
            self.config.logger.critical(
              'Error in creating crash source',
              exc_info=True
            )
            raise
        try:
            self.destination = self.config.destination.crashstorage(
              self.config.destination,
              quit_check_callback=self.quit_check
            )
        except Exception:
            self.config.logger.critical(
              'Error in creating crash destination',
              exc_info=True
            )
            raise

    #--------------------------------------------------------------------------
    def _setup_task_manager(self):
        """instantiate the threaded task manager to run the producer/consumer
        queue that is the heart of the processor."""
        self.config.logger.info('installing signal handers')
        signal.signal(signal.SIGTERM, respond_to_SIGTERM)
        signal.signal(signal.SIGHUP, respond_to_SIGTERM)
        self.task_manager = \
            self.config.producer_consumer.producer_consumer_class(
              self.config.producer_consumer,
              job_source_iterator=self.source_iterator,
              task_func=self.transform
            )

    #--------------------------------------------------------------------------
    def _cleanup(self):
        pass

    #--------------------------------------------------------------------------
    def main(self):
        """this main routine sets up the signal handlers, the source and
        destination crashstorage systems at the  theaded task manager.  That
        starts a flock of threads that are ready to shepherd crashes from
        the source to the destination."""

        self._setup_task_manager()
        self._setup_source_and_destination()
        self.task_manager.blocking_start(waiting_func=self.waiting_func)
        self._cleanup()
