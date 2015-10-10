# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    CrashIDNotFound,
    NullCrashStorage,
    MemoryDumpsMapping
)
# renaming to make it clear that this is not a DotDict from configman
from socorro.lib.util import DotDict as SocorroDotDict

from configman import Namespace
from functools import wraps


#==============================================================================
class RejectJob(Exception):
    """Used as an exception by the workers when they cannot load a crash for
    some reason.  When it is instantiated, the reason for the failure is
    given as the string to the constructor.  In the initial implementation
    of this class, the only use is on receiving a CrashIDNotFound exception.
    However, this class is available to be used for other reasons to reject
    crashes from within the worker methods."""
    pass


#------------------------------------------------------------------------------
def exception_wrapper(fn):
    """The worker methods classes all wrap access to the Crashstorage system
    in some exception handlers. Since that is boilerplate, it is offered here
    as a decorator on the calls to reduce code clutter."""
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except CrashIDNotFound, x:
            message = "%r could not be found" % x
            self.config.logger.warning(message, exc_info=True)
            raise RejectJob(message)
        except Exception as x:
            self.config.logger.error(
                "error reading raw_crash: %r",
                x,
                exc_info=True
            )
            raise
    return wrapper


#------------------------------------------------------------------------------
def NullTransform(*args, **kwargs):
    """when the app passes None to the FTSWorkerMethod deriviative, it is
    saying that we want the data to pass from the fetch to the save without
    being changed.  This is the case of the crashmover or the submitter apps.
    They don't change the data that flows through them.

    This method is a conveniennce that gets saved as the transformation method
    allowing the transformation method to be called sans exception handling.
    """
    pass



#==============================================================================
class FTSWorkerMethodBase(CrashStorageBase):
    """This base class for the worker methods class wraps all the access to the
    crashstorage system in exception handlers.

    On instantiation, the fetch store, the save store and the transformation
    method are all part of initialization.  That initialization happens in the
    FTS Apps' method called '_setup_source_and_destination'. The fetch and
    save crashstores are defined in configuration.  The transform is passed in
    as a parameter in the call.  The source of the transformation is defined
    by the application.

    For example, the ProcesorApp is a class that derives from the
    FetchTransformSaveApp.  It the ProcessorApp's configuration, it has two
    important parameters: the 'worker_task.worker_task_impl' and
    'processor.processor_class'.

    The 'worker_task.worker_task_impl' is a class from this hierachy.  For the
    processor, that is likely the class 'ProcessorWorkerMethod'.

    The 'processor.processor_class' for the processor is instatiated in the
    processor's '_setup_source_and_destination' method which is then passed
    down to the 'FetchTransformSaveApp' '_setup_source_and_destination' method
    as the 'transform_fn'.

    This class derives from the CrashStorage system of classes because it
    offers the same API and could be used as a 2 element crashstore, where the
    division of labor is between the save and get/fetch methods.  It deviates
    from the standard crashstorage hierarchy by being initialized with other
    crashstorage instances in its constructor rather than through the config
    system of dependency injection. The inclusion of this class in the
    crashstorage hierarchy is an early step in an evolutionary change that will
    see CrashStorage, FTS_worker_methods, and TransformRules all move toward
    drop in compatibility with each other.
    """
    required_config = Namespace()

    #--------------------------------------------------------------------------
    def __init__(
        self,
        config,
        fetch_store=None,
        save_store=None,
        transform_fn=None,
        quit_check=None
    ):
        super(FTSWorkerMethodBase, self).__init__(config)
        self.fetch_store = fetch_store if fetch_store else NullCrashStorage(
            config
        )
        self.save_store = save_store if save_store else NullCrashStorage(
            config
        )
        if transform_fn is None:
            transform_fn = NullTransform
        self.transformation_fn = transform_fn
        self.quick_check = quit_check

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # CrashStorage method forwards
    # methods in this section implement forwarding the crashstorage api methods
    # to the member crashstorage instances. All the 'save' methods forward to
    # the save crashstore, while the 'get' methods forward to the fetch
    # crashstore. All are wrapped with the standard exception handler decorator
    # so that they behave the same way
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    #--------------------------------------------------------------------------
    @exception_wrapper
    def save_raw_crash(self, raw_crash, dumps, crash_id):
        self.save_store.save_raw_crash(
            raw_crash,
            dumps,
            crash_id
        )

    #--------------------------------------------------------------------------
    @exception_wrapper
    def save_raw_crash_with_file_dumps(self, raw_crash, dumps, crash_id):
        self.save_store.save_raw_crash_with_file_dumps(
            raw_crash,
            dumps,
            crash_id
        )

    #--------------------------------------------------------------------------
    @exception_wrapper
    def save_processed(self, processed_crash):
        self.save_store.save_processed(processed_crash)

    #--------------------------------------------------------------------------
    @exception_wrapper
    def save_raw_and_processed(
        self,
        raw_crash,
        dumps,
        processed_crash,
        crash_id
    ):
        self.save_store.save_raw_and_processed(
            raw_crash,
            dumps,
            processed_crash,
            crash_id
        )

    #--------------------------------------------------------------------------
    @exception_wrapper
    def get_raw_crash(self, crash_id):
        return self.fetch_store.get_raw_crash(crash_id)

    #--------------------------------------------------------------------------
    @exception_wrapper
    def get_raw_dump(self, crash_id, name=None):
        return self.fetch_store.get_raw_dump(crash_id, name)

    #--------------------------------------------------------------------------
    @exception_wrapper
    def get_raw_dumps(self, crash_id):
        return self.fetch_store.get_raw_dumps(crash_id)

    #--------------------------------------------------------------------------
    @exception_wrapper
    def get_raw_dumps_as_files(self, crash_id):
        return self.fetch_store.get_raw_dumps_as_files(crash_id)

    #--------------------------------------------------------------------------
    @exception_wrapper
    def get_unredacted_processed(self, crash_id):
        return self.fetch_store.get_unredacted_processed(crash_id)

    #--------------------------------------------------------------------------
    @exception_wrapper
    def remove(self, crash_id):
        self.save_store.remove(crash_id)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # other methods
    # the methods in this section are misc support methods
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    #--------------------------------------------------------------------------
    def __call__(self, crash_id):
        """the classes in this hierarchy are functors, classes meant to be
        invoked as if they were functions.  Derived classes are to implement
        the '_call_impl' method to define  what the worker method does with the
        crashstorage instances.  This method adds a standard logging and
        exception handling so that all derived classes behave the same way."""
        self.config.logger.info("starting job: %s", crash_id)
        try:
            self._call_impl(crash_id)
            self.config.logger.info("finished successful job: %s", crash_id)
        except Exception, x:
            self.config.logger.warning(
                'finished failed job: %s (%r)',
                crash_id,
                x
            )
            if isinstance(x, RejectJob):
                return
            raise

    #--------------------------------------------------------------------------
    def _call_impl(self, crash_id):
        """each derived class is to implement this method to define how the
        FTS app is to interact with the crashstorage instances.  For example:
        read a raw_crash from the fetch crashstore, transform it in some
        manner, then save it to the save crashstore."""
        raise NotImplementedError()


#==============================================================================
class RawCrashCopyWorkerMethod(FTSWorkerMethodBase):
    """this worker method implementation reads raw crashes and dumps from the
    fetch crashstore, applies a transformation and then saves them to the
    save crashstore.  If the transformation is the NullTransformation (do not
    change the raw crash or dumps), then this is the implementation of a
    copy function.  This is the method used by the SubmiterApp as it just
    copies crashes from one crash storage system and submits them unchanged
    to another."""

    #--------------------------------------------------------------------------
    def _call_impl(self, crash_id):
        raw_crash = self.get_raw_crash(crash_id)
        raw_dumps = self.get_raw_dumps(crash_id)

        # the following call implements a transformation of the raw_crashs,
        # and raw_dumps.  Since they are both MutableMappings, any changes
        # happen to directly to them rather than making new ones and returning
        # them.
        self.transformation_fn(raw_crash=raw_crash, raw_dumps=raw_dumps)
        # where did this transformation come from?  Who set it?
        # the transformation_fn was specified in the constructor for this
        # class.  Most likely a App instantiated this class in its
        # '_setup_source_and_destination' method.  Apps like the processor,
        # will instantiate their own transformation object.  The transformation
        # object is a functor, an object that defines __call__ and can be
        # called as a function.  Processor2015 defines a transformation object
        # based on the TransformRule system.

        self.save_raw_crash(raw_crash, raw_dumps, crash_id)


#==============================================================================
class RawCrashMoveWorkerMethod(RawCrashCopyWorkerMethod):
    """this worker method implementation derives from the copy class above, but
    adds the step of deleting the original raw_crash and dumps from the fetch
    crashstore after a successful copy.  This is the implementation of the
    worker method for CrashMoverApp"""

    #--------------------------------------------------------------------------
    def _call_impl(self, crash_id):
        self.config.logger.debug(
            'RawCrashMoveWorkerMethod._call_impl with %s',
            crash_id
        )
        super(RawCrashMoveWorkerMethod, self)._call_impl(crash_id)
        self.remove(crash_id)


#==============================================================================
class ProcessedCrashCopyWorkerMethod(FTSWorkerMethodBase):
    """this worker method implementation copies processed crashes from the
    fetch crashstore to the save crashstore.  With a null transformation, it
    just copies.  This implementation is useful there needs to be an ad hoc
    change to processed crashes to correct an error or add/remove information
    from the processed crashes.
    """

    #--------------------------------------------------------------------------
    def _call_impl(self, crash_id):
        self.config.logger.debug(
            'ProcessedCrashCopyWorkerMethod._call_impl with %s',
            crash_id
        )
        processed_crash = self.get_unredacted_processed(crash_id)

        # see the commentary in the similar call in the class
        # RawCrashCopyWorkerMethod above for an explaination of this call:
        self.transformation_fn(processed_crash=processed_crash)

        self.save_processed(processed_crash)


#==============================================================================
class CopyAllWorkerMethod(FTSWorkerMethodBase):
    """this worker method implementation copies raw_crashs, raw_dumps and
    processed crashes from the fetch crashstore to the save crashstore.  This
    is useful as the basis for an app that mirgrates from one storage location
    to another.  For example, if a Socorro installation has been running with
    a filesystem primary storage and needs to migrate to Amazon S3, an FTS App
    with this worker implemention will do the job."""

    #--------------------------------------------------------------------------
    def _call_impl(self, crash_id):
        self.config.logger.debug(
            'CopyAllWorkerMethod._call_impl with %s',
            crash_id
        )
        raw_crash = self.get_raw_crash(crash_id)
        raw_dumps = self.get_raw_dumps(crash_id)
        processed_crash = self.get_unredacted_processed(crash_id)

        # see the commentary in the similar call in the class
        # RawCrashCopyWorkerMethod above for an explaination of this call:
        processed_crash = self.transformation_fn(
            raw_crash=raw_crash,
            raw_dumps=raw_crash,
            processed_crash=processed_crash
        )

        self.save_raw_and_processed(
            raw_crash,
            raw_dumps,
            processed_crash,
            crash_id
        )


#==============================================================================
class ProcessorWorkerMethod(FTSWorkerMethodBase):
    """this worker method implementation has been optimized for the processor
    that needs to have the raw_dumps in the form of files on a filesystem.  It
    follows the same form of the CopyAllWorkerMethod above, but requires that
    raw_dumps get written to the file system, then ensures that any temporary
    files are removed when the worker is done."""

    #--------------------------------------------------------------------------
    def _call_impl(self, crash_id):
        raw_crash = self.get_raw_crash(crash_id)
        raw_dumps = self.get_raw_dumps_as_files(crash_id)
        try:
            try:
                processed_crash = self.get_unredacted_processed(crash_id)
            except RejectJob:
                # this just means that this crash was not previously processed
                # we'll start with an empty processed crash instead
                processed_crash = SocorroDotDict()

            # see the commentary in the similar call in the class
            # RawCrashCopyWorkerMethod above for an explaination of this call:
            processed_crash = self.transformation_fn(
                raw_crash=raw_crash,
                raw_dumps=raw_dumps,
                processed_crash=processed_crash
            )

            self.save_raw_and_processed(
                raw_crash,
                # while the processor will resave raw crashes, it declines
                # to resave the raw dumps, so it does not pass them into this
                # call
                None,
                processed_crash,
                crash_id
            )
            self.config.logger.info('saved - %s', crash_id)
        finally:
            raw_dumps.remove_temp_files()


#==============================================================================
class NoDumpsProcessorWorkerMethod(ProcessorWorkerMethod):
    """this worker method implementation has been optimized for the processor
    that needs to have the raw_dumps in the form of files on a filesystem.  It
    follows the same form of the CopyAllWorkerMethod above, but requires that
    raw_dumps get written to the file system, then ensures that any temporary
    files are removed when the worker is done."""

    #--------------------------------------------------------------------------
    def get_raw_dumps_as_files(self, crash_id):
        return MemoryDumpsMapping({})



