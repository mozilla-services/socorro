# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

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
2012, that's the union of reading a postgres jobs/crash_id table and fetching
the crash from HBase.  The transform phase is the running of minidump stackwalk
and production of the processed crash data.  The save phase is the union of
sending new crash records to Postgres; sending the processed crash to HBase;
the the submission of the crash_id to Elastic Search."""

import signal
from functools import partial

from configman import Namespace
from configman.converters import class_converter

from socorro.lib.task_manager import respond_to_SIGTERM
from socorro.app.generic_app import App, main  # main not used here, but
                                               # is imported from generic_app
                                               # into this scope to offer to
                                               # apps that derive from the
                                               # class defined here.


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
    # iterator 'new_crashes' and the accessors 'get_raw_crash' and
    # 'get_raw_dumps'
    required_config.source.add_option(
      'crashstorage_class',
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
      'crashstorage_class',
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

    ###########################################################################
    ### TODO: add a feature where clients of this class may register a waiting
    ### function.  The MainThread will run all the registered waiting
    ### functions at their configured interval.  A first application of this
    ### feature will be to allow periodic reloading of config data from a
    ### database.  Specifically, the skip list rules could be reloaded without
    ### having to restart the processor.
    ###########################################################################

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
                'socorro.external.fs.crashstorage.FSPermanentStorage',
            'destination.crashstorage_class':
                'socorro.external.fs.crashstorage.FSPermanentStorage',
        }


    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(FetchTransformSaveApp, self).__init__(config)
        self.waiting_func = None

    #--------------------------------------------------------------------------
    def source_iterator(self):
        """this iterator yields individual crash_ids from the source
        crashstorage class's 'new_crashes' method."""
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
    def transform(self, crash_id):
        """this default transform function only transfers raw data from the
        source to the destination without changing the data.  While this may
        be good enough for the raw crashmover, the processor would override
        this method to create and save processed crashes"""
        try:
            raw_crash = self.source.get_raw_crash(crash_id)
        except Exception as x:
            self.config.logger.error(
                "reading raw_crash: %s",
                str(x),
                exc_info=True
            )
            raw_crash = {}
        try:
            dumps = self.source.get_raw_dumps(crash_id)
        except Exception as x:
            self.config.logger.error(
                "reading dump: %s",
                str(x),
                exc_info=True
            )
            dumps = {}
        try:
            self.destination.save_raw_crash(raw_crash, dumps, crash_id)
        except Exception as x:
            self.config.logger.error(
                "writing raw: %s",
                str(x),
                exc_info=True
            )
        else:
            try:
                self.source.remove(crash_id)
            except Exception as x:
                self.config.logger.error(
                    "removing raw: %s",
                    str(x),
                    exc_info=True
                )


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
            self.source = self.config.source.crashstorage_class(
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
            self.destination = self.config.destination.crashstorage_class(
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
        respond_to_SIGTERM_with_logging = partial(
            respond_to_SIGTERM,
            logger=self.config.logger
        )
        signal.signal(signal.SIGTERM, respond_to_SIGTERM_with_logging)
        self.task_manager = \
            self.config.producer_consumer.producer_consumer_class(
              self.config.producer_consumer,
              job_source_iterator=self.source_iterator,
              task_func=self.transform
            )
        self.config.executor_identity = self.task_manager.executor_identity

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
