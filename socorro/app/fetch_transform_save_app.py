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

from socorrolib.lib.task_manager import respond_to_SIGTERM
from socorrolib.app.generic_app import App, main  # main not used here, but
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
        default='socorrolib.lib.threaded_task_manager.ThreadedTaskManager',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'number_of_submissions',
        doc="the number of crashes to submit (all, forever, 1...)",
        short_form='n',
        default='forever'
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
            'socorro.external.fs.crashstorage.FSPermanentStorage',
            'destination.crashstorage_class':
            'socorro.external.fs.crashstorage.FSPermanentStorage',
        }

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(FetchTransformSaveApp, self).__init__(config)
        self.waiting_func = None
        # select the iterator type based on the "number_of_submissions" config
        self.source_iterator = {
            'forever': self._infinite_iterator,
            'all': self._all_iterator,
        }.get(config.number_of_submissions, self._limited_iterator)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # iterator section
    #
    # the following methods setup a nested hierarchy of iterators.  Each layer
    # in the hierarchy adds a feature to the enclosed iterator.

    # The  iterator at the core, the innermost, will yield a list of crash_ids
    # from some source. A subclass may define its own source and makes it
    # available by overriding the method "_create_iter".
    #
    # That innermost iterator is then wrapped by the "_basic_iterator" method.
    # this iterator changes the form of the yielded values to the (*args,
    # **kwargs) as required by the TaskManager.  It also gives derived classes
    # the oportunity to run callbacks between each iteration or at the point
    # that the innermost iterator is exhausted.
    #
    # The outermost layer of the iterator nesting imposes length limitations
    # on the iterators.  Controlled by the configuration parameter
    # "number_of_submissions" this iterator can be limit to an exact number
    # of iterations, set to run forever, or run only until the natural
    # exhaustion of the innermost iterator.
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    #--------------------------------------------------------------------------
    def _create_iter(self):
        # the actual mechanism of creating the iterator to be overridden in
        # subclasses based on what they want to iterate over.  In this default,
        # iteration will come from the crashstorage instance defined as
        # "source".  This works for the crashmover where the generally used
        # source is the file system walking class.
        return self.source.new_crashes()

    #--------------------------------------------------------------------------
    def _action_between_each_iteration(self):
        """an action to take after an item has been yielded by the iterator.
        This method is to be overridden by derived classes"""
        pass

    #--------------------------------------------------------------------------
    def _action_after_iteration_completes(self):
        """an action to be done when the iterator returned by the
        "_create_iter" method is exhausted.  This method is to be overridden
        in base classes that might need to do something special at that point.
        examples may be simple logging, waiting, or resetting the iteration
        system for the next loop."""
        pass

    #--------------------------------------------------------------------------
    def _basic_iterator(self):
        """this iterator yields individual crash_ids and/or Nones from the
        iterator specified by the "_create_iter" method. Bare values yielded
        by the "_create_iter" method get wrapped into an *args, **kwargs form.
        That form is then used by the task manager as the arguments to the
        worker function."""
        for x in self._create_iter():
            if x is None or isinstance(x, tuple):
                yield x
            else:
                yield ((x,), {})
            self._action_between_each_iteration()
        else:
            # when the iterator is exhausted, yield None as this is an
            # indicator to some of the clients to take an action.
            # This is a moribund action, but in this current refactoring
            # we don't want to change old behavior
            yield None
        self._action_after_iteration_completes()

    #--------------------------------------------------------------------------
    def _infinite_iterator(self):
        """this iterator wraps the "_basic_iterator" when the configuration
        specifies that the "number_of_submissions" is set to "forever".
        Whenever the "_basic_iterator" is exhausted, it is called again to
        restart the iteration.  It is up to the implementation of the innermost
        iterator to define what starting over means.  Some iterators may
        repeat exactly what they did before, while others may iterate over
        new values"""
        while True:
            for crash_id in self._basic_iterator():
                if self._filter_disallowed_values(crash_id):
                    continue
                yield crash_id

    #--------------------------------------------------------------------------
    def _all_iterator(self):
        """this is the iterator for the case when "number_of_submissions" is
        set to "all".  It goes through the innermost iterator exactly once
        and raises the StopIteration exception when that innermost iterator is
        exhausted"""
        for crash_id in self._basic_iterator():
            if crash_id is None:
                break
            yield crash_id

    #--------------------------------------------------------------------------
    def _limited_iterator(self):
        """this is the iterator for the case when "number_of_submissions" is
        set to an integer.  It goes through the innermost iterator exactly the
        number of times specified by "number_of_submissions"  To do that, it
        might run the innermost iterator to exhaustion.  If that happens, that
        innermost iterator is called again to start over.  It is up to the
        implementation of the innermost iteration to define what starting
        over means.  Some iterators may repeat exactly what they did before,
        while others may iterate over new values"""
        i = 0
        while True:
            for crash_id in self._basic_iterator():
                if self._filter_disallowed_values(crash_id):
                    continue
                if crash_id is None:
                    # it's ok to yield None, however, we don't want it to
                    # be counted as a yielded value
                    yield crash_id
                    continue
                if i == int(self.config.number_of_submissions):
                    # break out of inner loop, abandoning the wrapped iter
                    break
                i += 1
                yield crash_id
            # repeat the quit test, to break out of the outer loop and
            # if necessary, prevent recycling the wrapped iter
            if i == int(self.config.number_of_submissions):
                break

    #--------------------------------------------------------------------------
    def _filter_disallowed_values(self, current_value):
        """in this base class there are no disallowed values coming from the
        iterators.  Other users of these iterator may have some standards and
        can detect and reject them here"""
        return False

    #--------------------------------------------------------------------------
    def transform(
        self,
        crash_id,
        finished_func=(lambda: None),
    ):
        try:
            self._transform(crash_id)
        finally:
            # no matter what causes this method to end, we need to make sure
            # that the finished_func gets called. If the new crash source is
            # RabbitMQ, this is what removes the job from the queue.
            try:
                finished_func()
            except Exception, x:
                # when run in a thread, a failure here is not a problem, but if
                # we're running all in the same thread, a failure here could
                # derail the the whole processor. Best just log the problem
                # so that we can continue.
                self.config.logger.error(
                    'Error completing job %s: %s',
                    crash_id,
                    x,
                    exc_info=True
                )

    #--------------------------------------------------------------------------
    def _transform(self, crash_id):
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
            self.config.logger.info('saved - %s', crash_id)
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
        # set up the signal handler for dealing with SIGTERM. the target should
        # be this app instance so the signal handler can reach in and set the
        # quit flag to be True.  See the 'respond_to_SIGTERM' method for the
        # more information
        respond_to_SIGTERM_with_logging = partial(
            respond_to_SIGTERM,
            target=self
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
    def close(self):
        try:
            self.source.close()
        except AttributeError:
            # this source class has no close, we can ignore that & move on
            pass
        try:
            self.destination.close()
        except AttributeError:
            # this destination class has no close, we can ignore that & move on
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
        self.close()
        self.config.logger.info('done.')


#==============================================================================
class FetchTransformSaveWithSeparateNewCrashSourceApp(FetchTransformSaveApp):
    required_config = Namespace()
    required_config.namespace('new_crash_source')
    required_config.new_crash_source.add_option(
        'new_crash_source_class',
        doc='an iterable that will stream crash_ids needing processing',
        default='',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def _create_iter(self):
        # while the base class ties the iterator to the class specified as the
        # crash data "source", this class introduces a different stream of
        # crash_ids in the form of the "new_crash_source_class".  While this is
        # also typically tied to a crashstorage class, it doesn't have to be
        # the same class as the "source".  For example, the "source" may be
        # AmazonS3 but the stream of crash_ids may be from RabbitMQ or a
        # PG query
        return self.new_crash_source.new_crashes()

    #--------------------------------------------------------------------------
    def _setup_source_and_destination(self):
        """use the base class to setup the source and destinations but add to
        that setup the instantiation of the "new_crash_source" """
        super(FetchTransformSaveWithSeparateNewCrashSourceApp, self) \
            ._setup_source_and_destination()
        if self.config.new_crash_source.new_crash_source_class:
            self.new_crash_source = \
                self.config.new_crash_source.new_crash_source_class(
                    self.config.new_crash_source,
                    name=self.app_instance_name,
                    quit_check_callback=self.quit_check
                )
        else:
            # the configuration failed to provide a "new_crash_source", fall
            # back to tying the "new_crash_source" to the "source".
            self.new_crash_source = self.source

    #--------------------------------------------------------------------------
    def close(self):
        super(FetchTransformSaveWithSeparateNewCrashSourceApp, self).close()
        if self.source != self.new_crash_source:
            try:
                self.new_crash_source.close()
            except AttributeError:
                # the new_crash_source has no close, move on without it
                pass
