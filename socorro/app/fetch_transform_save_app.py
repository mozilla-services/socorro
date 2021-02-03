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

from functools import partial
import signal

from configman import Namespace
from configman.converters import class_converter

from socorro.lib.task_manager import respond_to_SIGTERM
from socorro.app.socorro_app import App


class FetchTransformSaveApp(App):
    """Fetch/transform/save apps."""

    app_name = "fetch_transform_save_app"
    app_version = "0.1"
    app_description = __doc__

    required_config = Namespace()
    # The queue class has an iterator for work items to be processed.
    required_config.namespace("queue")
    required_config.queue.add_option(
        "crashqueue_class",
        doc="an iterable that will stream work items for processing",
        default="",
        from_string_converter=class_converter,
    )

    # The source class has methods to fetch the data to use.
    required_config.source = Namespace()
    required_config.source.add_option(
        "crashstorage_class",
        doc="the source storage class",
        default="socorro.external.fs.crashstorage.FSPermanentStorage",
        from_string_converter=class_converter,
    )

    # The destination class has methods to save the transformed data to storage.
    required_config.destination = Namespace()
    required_config.destination.add_option(
        "crashstorage_class",
        doc="the destination storage class",
        default="socorro.external.fs.crashstorage.FSPermanentStorage",
        from_string_converter=class_converter,
    )

    required_config.producer_consumer = Namespace()
    required_config.producer_consumer.add_option(
        "producer_consumer_class",
        doc="the class implements a threaded producer consumer queue",
        default="socorro.lib.threaded_task_manager.ThreadedTaskManager",
        from_string_converter=class_converter,
    )

    def __init__(self, config):
        super().__init__(config)
        self.waiting_func = None

    def _basic_iterator(self):
        """Yield ``(*args, **kwargs)`` tuples of work."""
        for x in self.queue.new_crashes():
            if x is None or isinstance(x, tuple):
                yield x
            else:
                yield ((x,), {})
        yield None

    def source_iterator(self):
        """Iterate infinitely yielding crash ids."""
        while True:
            yield from self._basic_iterator()

    def transform(self, crash_id, finished_func=(lambda: None)):
        try:
            self._transform(crash_id)
        finally:
            # no matter what causes this method to end, we need to make sure
            # that the finished_func gets called. If the new crash source is
            # Pub/Sub, this is what removes the job from the queue.
            try:
                finished_func()
            except Exception as x:
                # when run in a thread, a failure here is not a problem, but if
                # we're running all in the same thread, a failure here could
                # derail the the whole processor. Best just log the problem
                # so that we can continue.
                self.logger.error(
                    "Error completing job %s: %s", crash_id, x, exc_info=True
                )

    def _transform(self, crash_id):
        """this default transform function only transfers raw data from the
        source to the destination without changing the data.  While this may
        be good enough for the raw crashmover, the processor would override
        this method to create and save processed crashes"""
        try:
            raw_crash = self.source.get_raw_crash(crash_id)
        except Exception as x:
            self.logger.error("reading raw_crash: %s", str(x), exc_info=True)
            raw_crash = {}
        try:
            dumps = self.source.get_raw_dumps(crash_id)
        except Exception as x:
            self.logger.error("reading dump: %s", str(x), exc_info=True)
            dumps = {}
        try:
            self.destination.save_raw_crash(raw_crash, dumps, crash_id)
            self.logger.info("saved - %s", crash_id)
        except Exception as x:
            self.logger.error("writing raw: %s", str(x), exc_info=True)
        else:
            try:
                self.source.remove(crash_id)
            except Exception as x:
                self.logger.error("removing raw: %s", str(x), exc_info=True)

    def _setup_source_and_destination(self):
        """Instantiate queue, source, and destination classes."""
        self.queue = self.config.queue.crashqueue_class(
            self.config.queue,
            namespace=self.app_instance_name,
        )
        self.source = self.config.source.crashstorage_class(
            self.config.source,
            namespace=self.app_name,
        )
        self.destination = self.config.destination.crashstorage_class(
            self.config.destination,
            namespace=self.app_name,
        )

    def _setup_task_manager(self):
        """instantiate the threaded task manager to run the producer/consumer
        queue that is the heart of the processor."""
        self.logger.info("installing signal handers")
        # set up the signal handler for dealing with SIGTERM. the target should
        # be this app instance so the signal handler can reach in and set the
        # quit flag to be True.  See the 'respond_to_SIGTERM' method for the
        # more information
        respond_to_SIGTERM_with_logging = partial(respond_to_SIGTERM, target=self)
        signal.signal(signal.SIGTERM, respond_to_SIGTERM_with_logging)
        self.task_manager = self.config.producer_consumer.producer_consumer_class(
            self.config.producer_consumer,
            job_source_iterator=self.source_iterator,
            task_func=self.transform,
        )

    def close(self):
        try:
            self.queue.close()
        except AttributeError:
            pass
        try:
            self.source.close()
        except AttributeError:
            pass
        try:
            self.destination.close()
        except AttributeError:
            pass

    def main(self):
        """this main routine sets up the signal handlers, the source and
        destination crashstorage systems at the  theaded task manager.  That
        starts a flock of threads that are ready to shepherd crashes from
        the source to the destination."""

        self._setup_task_manager()
        self._setup_source_and_destination()
        self.task_manager.blocking_start(waiting_func=self.waiting_func)
        self.close()
        self.logger.info("done.")
