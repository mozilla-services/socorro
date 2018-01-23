# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""This is the base of the crashstorage system - a unified interfaces for
saving, fetching and iterating over raw crashes, dumps and processed crashes.
"""

import copy
import sys
import os
import collections
import datetime

from socorro.lib.util import DotDict as SocorroDotDict

from configman import Namespace, RequiredConfig
from configman.converters import class_converter
from configman.dotdict import DotDict as ConfigmanDotDict


def socorrodotdict_to_dict(sdotdict):
    """Takes a socorro.lib.util.DotDict and returns a dict

    This does a complete object traversal converting all instances of the
    things named DotDict to dict so it's deep-copyable.

    """
    def _dictify(thing):
        if isinstance(thing, collections.Mapping):
            return dict([(key, _dictify(val)) for key, val in thing.items()])
        elif isinstance(thing, basestring):
            return thing
        elif isinstance(thing, collections.Sequence):
            return [_dictify(item) for item in thing]
        return thing

    return _dictify(sdotdict)


class MemoryDumpsMapping(dict):
    """there has been a bifurcation in the crash storage data throughout the
    history of the classes.  The crash dumps have two different
    representations:

    1) a mapping of crash names to binary data blobs
    2) a mapping of crash names to file pathnames.

    It has been a manner of gentleman's agreement that two types do not mix.
    However, as the two methods have evolved in parallel the distinction has
    become more and more inconvenient.

    This class represents case 1 from above.  It is a mapping of crash dump
    names to binary representation of the dump.  Before using a mapping, a given
    crash store should call the "as_file_dumps_mapping" or
    "as_memory_dumps_mapping" depend on what that crashstorage implementation
    is going to need.
    """

    def as_file_dumps_mapping(self, crash_id, temp_path, dump_file_suffix):
        """convert this MemoryDumpMapping into a FileDumpsMappng by writing
        each of the dump to a filesystem."""
        name_to_pathname_mapping = FileDumpsMapping()
        for a_dump_name, a_dump in self.iteritems():
            if a_dump_name in (None, '', 'dump'):
                a_dump_name = 'upload_file_minidump'
            dump_pathname = os.path.join(
                temp_path,
                "%s.%s.TEMPORARY%s" % (
                    crash_id,
                    a_dump_name,
                    dump_file_suffix
                )
            )
            name_to_pathname_mapping[a_dump_name] = dump_pathname
            with open(dump_pathname, 'wb') as f:
                f.write(a_dump)
        return name_to_pathname_mapping

    def as_memory_dumps_mapping(self):
        """this is alrady a MemoryDumpMapping so we can just return self
        without having to do any conversion."""
        return self


class FileDumpsMapping(dict):
    """there has been a bifurcation in the crash storage data throughout the
    history of the classes.  The crash dumps have two different
    representations:

    1) a mapping of crash names to binary data blobs
    2) a mapping of crash names to file pathnames.

    It has been a manner of gentleman's agreement that two types do not mix.
    However, as the two methods have evolved in parallel the distinction has
    become more and more inconvenient.


    This class represents case 2 from above.  It is a mapping of crash dump
    names to pathname of a file containing the dump.  Before using a mapping,
    a given crash store should call the "as_file_dumps_mapping" or
    "as_memory_dumps_mapping" depend on what that crashstorage implementation
    is going to need.
    """

    def as_file_dumps_mapping(
        self,
        *args,
        **kwargs
    ):
        """this crash is already a FileDumpsMapping, so we can just return self.
        However, the arguments to this function are ignored.  The purpose of
        this class is not to move crashes around on filesytem. The arguments
        a solely for maintaining a consistent interface with the companion
        MemoryDumpsMapping class."""
        return self

    def as_memory_dumps_mapping(self):
        """convert this into a MemoryDumpsMapping by opening and reading each
        of the dumps in the mapping."""
        in_memory_dumps = MemoryDumpsMapping()
        for dump_key, dump_path in self.iteritems():
            with open(dump_path) as f:
                in_memory_dumps[dump_key] = f.read()
        return in_memory_dumps


class Redactor(RequiredConfig):
    """This class is the implementation of a functor for in situ redacting
    of sensitive keys from a mapping.  Keys that are to be redacted are placed
    in the configuration under the name 'forbidden_keys'.  They may take the
    form of dotted keys with subkeys.  For example, "a.b.c" means that the key,
    "c" is to be redacted."""
    required_config = Namespace()
    required_config.add_option(
        name='forbidden_keys',
        doc='a list of keys not allowed in a redacted processed crash',
        default="url, email, user_id, exploitability,"
                "json_dump.sensitive,"
                "upload_file_minidump_flash1.json_dump.sensitive,"
                "upload_file_minidump_flash2.json_dump.sensitive,"
                "upload_file_minidump_browser.json_dump.sensitive,"
                "memory_info",
        reference_value_from='resource.redactor',
    )

    def __init__(self, config):
        self.config = config
        self.forbidden_keys = [
            x.strip() for x in self.config.forbidden_keys.split(',')
        ]

    def redact(self, a_mapping):
        """this is the function that does the redaction."""
        for a_key in self.forbidden_keys:
            sub_mapping = a_mapping
            sub_keys = a_key.split('.')
            try:
                for a_sub_key in sub_keys[:-1]:  # step through the subkeys
                    sub_mapping = sub_mapping[a_sub_key.strip()]
                del sub_mapping[sub_keys[-1]]
            except KeyError:
                # this is okay, our key was already deleted by
                # another pattern that matched at a higher level
                pass

    def __call__(self, a_mapping):
        self.redact(a_mapping)


class CrashIDNotFound(Exception):
    pass


class CrashStorageBase(RequiredConfig):
    """the base class for all crash storage classes"""
    required_config = Namespace()
    required_config.add_option(
        name="redactor_class",
        doc="the name of the class that implements a 'redact' method",
        default=Redactor,
        reference_value_from='resource.redactor',
    )

    def __init__(self, config, quit_check_callback=None):
        """base class constructor

        parameters:
            config - a configman dot dict holding configuration information
            quit_check_callback - a function to be called periodically during
                                  long running operations.  It should check
                                  whatever the client app uses to detect a
                                  quit request and raise a KeyboardInterrupt.
                                  All derived classes should be prepared to
                                  shut down cleanly on getting such an
                                  exception from a call to this function

        instance varibles:
            self.config - a reference to the config mapping
            self.quit_check - a reference to the quit detecting callback
            self.logger - convience shortcut to the logger in the config
            self.exceptions_eligible_for_retry - a collection of non-fatal
                    exceptions that can be raised by a given storage
                    implementation.  This may be fetched by a client of the
                    crashstorge so that it can determine if it can try a failed
                    storage operation again."""
        self.config = config
        if quit_check_callback:
            self.quit_check = quit_check_callback
        else:
            self.quit_check = lambda: False
        self.logger = config.logger
        self.exceptions_eligible_for_retry = ()
        self.redactor = config.redactor_class(config)

    def close(self):
        """some implementations may need explicit closing."""
        pass

    def is_mutator(self):
        """Whether this storage class mutates the crash or not

        By default, crash storage classes don't mutate the crash.

        """
        return False

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        """this method that saves  both the raw_crash and the dump, must be
        overridden in any implementation.

        Why is does this base implementation just silently do nothing rather
        than raise a NotImplementedError?  Implementations of crashstorage
        are not required to implement the entire api.  Some may save only
        processed crashes but may be bundled (see the PolyCrashStorage class)
        with other crashstorage implementations.  Rather than having a non-
        implenting class raise an exeception that would derail the other
        bundled operations, the non-implementing storageclass will just
        quietly do nothing.

        parameters:
            raw_crash - a mapping containing the raw crash meta data.  It is
                        often saved as a json file, but here it is in the form
                        of a dict.
            dumps - a dict of dump name keys and binary blob values
            crash_id - the crash key to use for this crash"""
        pass

    def save_raw_crash_with_file_dumps(self, raw_crash, dumps, crash_id):
        """this method that saves  both the raw_crash and the dump and must be
        overridden in any implementation that wants a different behavior.  It
        assumes that the dumps are in the form of paths to files and need to
        be converted to memory_dumps

        parameters:
            raw_crash - a mapping containing the raw crash meta data.  It is
                        often saved as a json file, but here it is in the form
                        of a dict.
            dumps - a dict of dump name keys and paths to file system locations
                    for the dump data
            crash_id - the crash key to use for this crash"""
        self.save_raw_crash(
            raw_crash,
            dumps.as_memory_dumps_mapping(),
            crash_id
        )

    def save_processed(self, processed_crash):
        """this method saves the processed_crash and must be overridden in
        anything that chooses to implement it.

        Why is does this base implementation just silently do nothing rather
        than raise a NotImplementedError?  Implementations of crashstorage
        are not required to implement the entire api.  Some may save only
        processed crashes but may be bundled (see the PolyCrashStorage class)
        with other crashstorage implementations.  Rather than having a non-
        implenting class raise an exeception that would derail the other
        bundled operations, the non-implementing storageclass will just
        quietly do nothing.

        parameters:
            processed_crash - a mapping containing the processed crash"""
        pass

    def save_raw_and_processed(self, raw_crash, dumps, processed_crash,
                               crash_id):
        """Mainly for the convenience and efficiency of the processor,
        this unified method combines saving both raw and processed crashes.

        parameters:
            raw_crash - a mapping containing the raw crash meta data. It is
                        often saved as a json file, but here it is in the form
                        of a dict.
            dumps - a dict of dump name keys and binary blob values
            processed_crash - a mapping containing the processed crash
            crash_id - the crash key to use for this crash"""
        self.save_raw_crash(raw_crash, dumps, crash_id)
        self.save_processed(processed_crash)

    def get_raw_crash(self, crash_id):
        """the default implementation of fetching a raw_crash

        parameters:
           crash_id - the id of a raw crash to fetch"""
        raise NotImplementedError("get_raw_crash is not implemented")

    def get_raw_dump(self, crash_id, name=None):
        """the default implementation of fetching a dump

        parameters:
           crash_id - the id of a dump to fetch
           name - the name of the dump to fetch"""
        raise NotImplementedError("get_raw_dump is not implemented")

    def get_raw_dumps(self, crash_id):
        """the default implementation of fetching all the dumps

        parameters:
           crash_id - the id of a dump to fetch"""
        raise NotImplementedError("get_raw_dumps is not implemented")

    def get_raw_dumps_as_files(self, crash_id):
        """the default implementation of fetching all the dumps as files on
        a file system somewhere.  returns a list of pathnames.

        parameters:
           crash_id - the id of a dump to fetch"""
        raise NotImplementedError("get_raw_dumps is not implemented")

    def get_processed(self, crash_id):
        """the default implementation of fetching a processed_crash.  This
        method should not be overridden in subclasses unless the intent is to
        alter the redaction process.

        parameters:
           crash_id - the id of a processed_crash to fetch"""
        processed_crash = self.get_unredacted_processed(crash_id)
        self.redactor(processed_crash)
        return processed_crash

    def get_unredacted_processed(self, crash_id):
        """the implementation of fetching a processed_crash with no redaction

        parameters:
           crash_id - the id of a processed_crash to fetch"""
        raise NotImplementedError(
            "get_unredacted_processed is not implemented"
        )

    def remove(self, crash_id):
        """delete a crash from storage

        parameters:
           crash_id - the id of a crash to fetch"""
        raise NotImplementedError("remove is not implemented")

    def new_crashes(self):
        """a generator handing out a sequence of crash_ids of crashes that are
        considered to be new.  Each implementation can interpret the concept
        of "new" in an implementation specific way.  To be useful, derived
        class ought to override this method.
        """
        return []

    def ack_crash(self, crash_id):
        """overridden by subclasses that must acknowledge a successful use of
        an item pulled from the 'new_crashes' generator. """
        return crash_id


class NullCrashStorage(CrashStorageBase):
    """a testing crashstorage that silently ignores everything it's told to do
    """
    def get_raw_crash(self, crash_id):
        """the default implementation of fetching a raw_crash

        parameters:
           crash_id - the id of a raw crash to fetch"""
        return SocorroDotDict()

    def get_raw_dump(self, crash_id, name):
        """the default implementation of fetching a dump

        parameters:
           crash_id - the id of a dump to fetch"""
        return ''

    def get_raw_dumps(self, crash_id):
        """the default implementation of fetching all the dumps

        parameters:
           crash_id - the id of a dump to fetch"""
        return SocorroDotDict()

    def get_raw_dumps_as_files(self, crash_id):
        """the default implementation of fetching all the dumps

        parameters:
           crash_id - the id of a dump to fetch"""
        return SocorroDotDict()

    def get_unredacted_processed(self, crash_id):
        """the default implementation of fetching a processed_crash

        parameters:
           crash_id - the id of a processed_crash to fetch"""
        return SocorroDotDict()

    def remove(self, crash_id):
        """delete a crash from storage

        parameters:
           crash_id - the id of a crash to fetch"""
        pass


class PolyStorageError(Exception, collections.MutableSequence):
    """an exception container holding a sequence of exceptions with tracebacks.

    parameters:
        message - an optional over all error message
    """
    def __init__(self, *args):
        super(PolyStorageError, self).__init__(*args)
        self.exceptions = []  # the collection

    def gather_current_exception(self):
        """append the currently active exception to the collection"""
        self.exceptions.append(sys.exc_info())

    def has_exceptions(self):
        """the boolean opposite of is_empty"""""
        return bool(self.exceptions)

    def __len__(self):
        """how many exceptions are stored?
        this method is required by the MutableSequence abstract base class"""
        return len(self.exceptions)

    def __iter__(self):
        """start an iterator over the squence.
        this method is required by the MutableSequence abstract base class"""
        return iter(self.exceptions)

    def __contains__(self, value):
        """search the sequence for a value and return true if it is present
        this method is required by the MutableSequence abstract base class"""

        return self.exceptions.__contains__(value)

    def __getitem__(self, index):
        """fetch a specific exception
        this method is required by the MutableSequence abstract base class"""
        return self.exceptions.__getitem__(index)

    def __setitem__(self, index, value):
        """change the value for an index in the sequence
        this method is required by the MutableSequence abstract base class"""
        self.exceptions.__setitem__(index, value)

    def __str__(self):
        output = []
        if self.args:
            output.append(self.args[0])
        for e in self.exceptions:
            output.append(repr(e[1]).encode('ascii', 'ignore'))
        return ','.join(output)


class StorageNamespaceList(collections.Sequence):
    """A sequence of configuration namespaces for crash stores.

    Functionally, this is a list of strings that correspond to a configuration
    namespace under the key ``destination.{namespace}``. Each entry creates a
    new crashstorage instance that crashes are saved to.

    We use a custom subclass so that we can add ``self.required_config``, which
    contains options for each crashstorage class. Doing this lets configman find
    and include any config options that those classes define via their own
    ``required_config`` attributes.
    """
    def __init__(self, storage_namespaces):
        self.storage_namespaces = storage_namespaces
        self.required_config = Namespace()

        for storage_name in storage_namespaces:
            self.required_config[storage_name] = Namespace()
            self.required_config[storage_name].add_option(
                'crashstorage_class',
                from_string_converter=class_converter,
            )

    def __len__(self):
        return len(self.storage_namespaces)

    def __getitem__(self, key):
        return self.storage_namespaces[key]

    def to_str(self):
        return ','.join(self.storage_namespaces)

    @classmethod
    def converter(cls, storage_namespace_list_str):
        """from_string_converter-compatible factory method.

        parameters:
            storage_namespace_list_str - comma-separated list of config
                namespaces containing info about crash storages.
        """
        namespaces = [name.strip() for name in storage_namespace_list_str.split(',')]
        return cls(namespaces)


class PolyCrashStorage(CrashStorageBase):
    """a crashstorage implementation that encapsulates a collection of other
    crashstorage instances.  Any save operation applied to an instance of this
    class will be applied to all the crashstorge in the collection.

    This class is useful for 'save' operations only.  It does not implement
    the 'get' operations.

    The contained crashstorage instances are specified in the configuration.
    Each key in the `storage_namespaces`` config option will be used to create
    a crashstorage instance that this saves to. The keys are namespaces in the
    config, and any options defined under those namespaces will be isolated
    within the config passed to the crashstorage instance. For example:

    .. code-block:: ini
        destination.crashstorage_namespaces=postgres,s3

        destination.postgres.crashstorage_class=module.path.PostgresStorage
        destination.postgres.my.config=Postgres

        destination.s3.crashstorage_class=module.path.S3Storage
        destination.s3.my.config=S3

    With this config, there are two crashstorage instances this class will
    create: one for Postgres, and one for S3. The PostgresStorage instance will
    see the ``my.config`` option as being set to "Postgres", while the S3Storage
    instance will see ``my.config`` set to "S3".
    """
    required_config = Namespace()
    required_config.add_option(
        'storage_namespaces',
        doc='a comma delimited list of storage namespaces',
        default='',
        from_string_converter=StorageNamespaceList.converter,
        likely_to_be_changed=True,
    )

    def __init__(self, config, quit_check_callback=None):
        """instantiate all the subordinate crashstorage instances

        parameters:
            config - a configman dot dict holding configuration information
            quit_check_callback - a function to be called periodically during
                                  long running operations.

        instance variables:
            self.storage_namespaces - the list of the namespaces in which the
                                      subordinate instances are stored.
            self.stores - instances of the subordinate crash stores

        """
        super(PolyCrashStorage, self).__init__(config, quit_check_callback)
        self.storage_namespaces = config.storage_namespaces
        self.stores = ConfigmanDotDict()
        for a_namespace in self.storage_namespaces:
            self.stores[a_namespace] = config[a_namespace].crashstorage_class(
                config[a_namespace],
                quit_check_callback
            )

    def close(self):
        """iterate through the subordinate crash stores and close them.
        Even though the classes are closed in sequential order, all are
        assured to close even if an earlier one raises an exception.  When all
        are closed, any exceptions that were raised are reraised in a
        PolyStorageError

        raises:
          PolyStorageError - an exception container holding a list of the
                             exceptions raised by the subordinate storage
                             systems"""
        storage_exception = PolyStorageError()
        for a_store in self.stores.itervalues():
            try:
                a_store.close()
            except Exception as x:
                self.logger.error('%s failure: %s', a_store.__class__,
                                  str(x))
                storage_exception.gather_current_exception()
        if storage_exception.has_exceptions():
            raise storage_exception

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        """iterate through the subordinate crash stores saving the raw_crash
        and the dump to each of them.

        parameters:
            raw_crash - the meta data mapping
            dumps - a mapping of dump name keys to dump binary values
            crash_id - the id of the crash to use"""
        storage_exception = PolyStorageError()
        for a_store in self.stores.itervalues():
            self.quit_check()
            try:
                a_store.save_raw_crash(raw_crash, dumps, crash_id)
            except Exception as x:
                self.logger.error('%s failure: %s', a_store.__class__,
                                  str(x))
                storage_exception.gather_current_exception()
        if storage_exception.has_exceptions():
            raise storage_exception

    def save_processed(self, processed_crash):
        """iterate through the subordinate crash stores saving the
        processed_crash to each of the.

        parameters:
            processed_crash - a mapping containing the processed crash"""
        storage_exception = PolyStorageError()
        for a_store in self.stores.itervalues():
            self.quit_check()
            try:
                a_store.save_processed(processed_crash)
            except Exception as x:
                self.logger.error('%s failure: %s', a_store.__class__,
                                  str(x), exc_info=True)
                storage_exception.gather_current_exception()
        if storage_exception.has_exceptions():
            raise storage_exception

    def save_raw_and_processed(self, raw_crash, dump, processed_crash,
                               crash_id):
        storage_exception = PolyStorageError()

        # Later we're going to need to clone this per every crash storage
        # in the loop. But, to save time, before we do that, convert the
        # processed crash which is a SocorroDotDict into a pure python
        # dict which we can more easily copy.deepcopy() operate on.
        processed_crash_as_dict = socorrodotdict_to_dict(processed_crash)
        raw_crash_as_dict = socorrodotdict_to_dict(raw_crash)

        for a_store in self.stores.itervalues():
            self.quit_check()
            try:
                actual_store = getattr(a_store, 'wrapped_object', a_store)

                if hasattr(actual_store, 'is_mutator') and actual_store.is_mutator():
                    # We do this because `a_store.save_raw_and_processed`
                    # expects the processed crash to be a DotDict but
                    # you can't deepcopy those, so we deepcopy the
                    # pure dict version and then dress it back up as a
                    # DotDict.
                    my_processed_crash = SocorroDotDict(
                        copy.deepcopy(processed_crash_as_dict)
                    )
                    my_raw_crash = SocorroDotDict(
                        copy.deepcopy(raw_crash_as_dict)
                    )
                else:
                    my_processed_crash = processed_crash
                    my_raw_crash = raw_crash

                a_store.save_raw_and_processed(
                    my_raw_crash,
                    dump,
                    my_processed_crash,
                    crash_id
                )
            except Exception:
                store_class = getattr(
                    a_store, 'wrapped_object', a_store.__class__
                )
                self.logger.error(
                    '%r failed (crash id: %s)',
                    store_class,
                    crash_id,
                    exc_info=True
                )
                storage_exception.gather_current_exception()
        if storage_exception.has_exceptions():
            raise storage_exception


class FallbackCrashStorage(CrashStorageBase):
    """This storage system has a primary and fallback subordinate storage
    systems.  If an exception is raised by the primary storage system during
    an operation, the operation is repeated on the fallback storage system.

    This class is useful for 'save' operations only.  It does not implement
    the 'get' operations."""
    required_config = Namespace()
    required_config.primary = Namespace()
    required_config.primary.add_option(
        'storage_class',
        doc='storage class for primary storage',
        default='',
        from_string_converter=class_converter
    )
    required_config.fallback = Namespace()
    required_config.fallback.add_option(
        'storage_class',
        doc='storage class for fallback storage',
        default='',
        from_string_converter=class_converter
    )

    def __init__(self, config, quit_check_callback=None):
        """instantiate the primary and secondary storage systems"""
        super(FallbackCrashStorage, self).__init__(config, quit_check_callback)
        self.primary_store = config.primary.storage_class(
            config.primary,
            quit_check_callback
        )
        self.fallback_store = config.fallback.storage_class(
            config.fallback,
            quit_check_callback
        )
        self.logger = self.config.logger

    def close(self):
        """close both storage systems.  The second will still be closed even
        if the first raises an exception. """
        poly_exception = PolyStorageError()
        for a_store in (self.primary_store, self.fallback_store):
            try:
                a_store.close()
            except NotImplementedError:
                pass
            except Exception:
                poly_exception.gather_current_exception()
        if len(poly_exception.exceptions) > 1:
            raise poly_exception

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        """save raw crash data to the primary.  If that fails save to the
        fallback.  If that fails raise the PolyStorageException

        parameters:
            raw_crash - the meta data mapping
            dumps - a mapping of dump name keys to dump binary values
            crash_id - the id of the crash to use"""
        try:
            self.primary_store.save_raw_crash(raw_crash, dumps, crash_id)
        except Exception:
            self.logger.critical('error in saving primary', exc_info=True)
            poly_exception = PolyStorageError()
            poly_exception.gather_current_exception()
            try:
                self.fallback_store.save_raw_crash(raw_crash, dumps, crash_id)
            except Exception:
                self.logger.critical('error in saving fallback', exc_info=True)
                poly_exception.gather_current_exception()
                raise poly_exception

    def save_processed(self, processed_crash):
        """save processed crash data to the primary.  If that fails save to the
        fallback.  If that fails raise the PolyStorageException

        parameters:
            processed_crash - a mapping containing the processed crash"""
        try:
            self.primary_store.save_processed(processed_crash)
        except Exception:
            self.logger.critical('error in saving primary', exc_info=True)
            poly_exception = PolyStorageError()
            poly_exception.gather_current_exception()
            try:
                self.fallback_store.save_processed(processed_crash)
            except Exception:
                self.logger.critical('error in saving fallback', exc_info=True)
                poly_exception.gather_current_exception()
                raise poly_exception

    def get_raw_crash(self, crash_id):
        """get a raw crash 1st from primary and if not found then try the
        fallback.

        parameters:
           crash_id - the id of a raw crash to fetch"""
        try:
            return self.primary_store.get_raw_crash(crash_id)
        except CrashIDNotFound:
            return self.fallback_store.get_raw_crash(crash_id)

    def get_raw_dump(self, crash_id, name=None):
        """get a named crash dump 1st from primary and if not found then try
        the fallback.

        parameters:
           crash_id - the id of a dump to fetch"""
        try:
            return self.primary_store.get_raw_dump(crash_id, name)
        except CrashIDNotFound:
            return self.fallback_store.get_raw_dump(crash_id, name)

    def get_raw_dumps(self, crash_id):
        """get all crash dumps 1st from primary and if not found then try
        the fallback.

        parameters:
           crash_id - the id of a dump to fetch"""
        try:
            return self.primary_store.get_raw_dumps(crash_id)
        except CrashIDNotFound:
            return self.fallback_store.get_raw_dumps(crash_id)

    def get_raw_dumps_as_files(self, crash_id):
        """get all crash dump pathnames 1st from primary and if not found then
        try the fallback.

        parameters:
           crash_id - the id of a dump to fetch"""
        try:
            return self.primary_store.get_raw_dumps_as_files(crash_id)
        except CrashIDNotFound:
            return self.fallback_store.get_raw_dumps_as_files(crash_id)

    def get_unredacted_processed(self, crash_id):
        """fetch an unredacted processed_crash

        parameters:
           crash_id - the id of a processed_crash to fetch"""
        try:
            return self.primary_store.get_unredacted_processed(crash_id)
        except CrashIDNotFound:
            return self.fallback_store.get_unredacted_processed(crash_id)

    def remove(self, crash_id):
        """delete a crash from storage

        parameters:
           crash_id - the id of a crash to fetch"""
        try:
            self.primary_store.remove(crash_id)
        except CrashIDNotFound:
            self.fallback_store.remove(crash_id)

    def new_crashes(self):
        """return an iterator that yields a list of crash_ids of raw crashes
        that were added to the file system since the last time this iterator
        was requested."""
        for a_crash in self.fallback_store.new_crashes():
            yield a_crash
        for a_crash in self.primary_store.new_crashes():
            yield a_crash


class MigrationCrashStorage(FallbackCrashStorage):
    required_config = Namespace()
    required_config.add_option(
        'date_threshold',
        default="150401",
        doc="a date before which seconday storage is to "
            "be used (YYYMMDD)",
    )

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        """save raw crash data to the primary storage iff the date embedded
        in the crash_id is greater or equal to the threshold, otherwise save
        to the fallback storage

        parameters:
            raw_crash - the meta data mapping
            dumps - a mapping of dump name keys to dump binary values
            crash_id - the id of the crash to use"""

        if crash_id[-6:] >= self.config.date_threshold:
            self.primary_store.save_raw_crash(raw_crash, dumps, crash_id)
        else:
            self.fallback_store.save_raw_crash(raw_crash, dumps, crash_id)

    def save_processed(self, processed_crash):
        """save processed crash data to the primary storage iff the date
        embedded in the crash_id is greater or equal to the threshold,
        otherwise save to the fallback storage

        parameters:
            processed_crash - a mapping containing the processed crash"""
        if processed_crash['crash_id'][-6:] >= self.config.date_threshold:
            self.primary_store.save_processed(processed_crash)
        else:
            self.fallback_store.save_processed(processed_crash)

    def get_raw_crash(self, crash_id):
        """get a raw crash from the primary if the crash_id embedded date is
        greater than or equal to the threshold, otherwise use the fallback

        parameters:
           crash_id - the id of a raw crash to fetch"""
        if crash_id[-6:] >= self.config.date_threshold:
            return self.primary_store.get_raw_crash(crash_id)
        else:
            return self.fallback_store.get_raw_crash(crash_id)

    def get_raw_dump(self, crash_id, name=None):
        """get a named crash dump 1from the primary if the crash_id embedded
        date is greater than or equal to the threshold, otherwise use the
        fallback

        parameters:
           crash_id - the id of a dump to fetch"""
        if crash_id[-6:] >= self.config.date_threshold:
            return self.primary_store.get_raw_dump(crash_id, name)
        else:
            return self.fallback_store.get_raw_dump(crash_id, name)

    def get_raw_dumps(self, crash_id):
        """get all crash dumps from the primary if the crash_id embedded date
        is greater than or equal to the threshold, otherwise use the fallback

        parameters:
           crash_id - the id of a dump to fetch"""
        if crash_id[-6:] >= self.config.date_threshold:
            return self.primary_store.get_raw_dumps(crash_id)
        else:
            return self.fallback_store.get_raw_dumps(crash_id)

    def get_raw_dumps_as_files(self, crash_id):
        """get all crash dump pathnames from the primary if the crash_id
        embedded date is greater than or equal to the threshold, otherwise
        use the fallback

        parameters:
           crash_id - the id of a dump to fetch"""
        if crash_id[-6:] >= self.config.date_threshold:
            return self.primary_store.get_raw_dumps_as_files(crash_id)
        else:
            return self.fallback_store.get_raw_dumps_as_files(crash_id)

    def get_unredacted_processed(self, crash_id):
        """fetch an unredacted processed_crash from the primary if the crash_id
        embedded date is greater than or equal to the threshold, otherwise use
        the fallback

        parameters:
           crash_id - the id of a processed_crash to fetch"""
        if crash_id[-6:] >= self.config.date_threshold:
            return self.primary_store.get_unredacted_processed(crash_id)
        else:
            return self.fallback_store.get_unredacted_processed(crash_id)

    def remove(self, crash_id):
        """delete a crash from storage

        parameters:
           crash_id - the id of a crash to fetch"""
        if crash_id[-6:] >= self.config.date_threshold:
            self.primary_store.remove(crash_id)
        else:
            self.fallback_store.remove(crash_id)


class PrimaryDeferredStorage(CrashStorageBase):
    """
    PrimaryDeferredStorage reads information from a raw crash and, based on a
    predicate function, selects either the primary or deferred storage to store
    a crash in.
    """
    required_config = Namespace()
    required_config.primary = Namespace()
    required_config.primary.add_option(
        'storage_class',
        doc='storage class for primary storage',
        default='',
        from_string_converter=class_converter
    )
    required_config.deferred = Namespace()
    required_config.deferred.add_option(
        'storage_class',
        doc='storage class for deferred storage',
        default='',
        from_string_converter=class_converter
    )
    required_config.add_option(
        'deferral_criteria',
        doc='criteria for deferring a crash',
        default='lambda crash: crash.get("legacy_processing")',
        from_string_converter=eval
    )

    def __init__(self, config, quit_check_callback=None):
        """instantiate the primary and deferred storage systems"""
        super(PrimaryDeferredStorage, self).__init__(
            config,
            quit_check_callback
        )
        self.primary_store = config.primary.storage_class(
            config.primary,
            quit_check_callback
        )
        self.deferred_store = config.deferred.storage_class(
            config.deferred,
            quit_check_callback
        )
        self.logger = self.config.logger

    def close(self):
        """close both storage systems.  The second will still be closed even
        if the first raises an exception. """
        poly_exception = PolyStorageError()
        for a_store in (self.primary_store, self.deferred_store):
            try:
                a_store.close()
            except NotImplementedError:
                pass
            except Exception:
                poly_exception.gather_current_exception()
        if len(poly_exception.exceptions) > 1:
            raise poly_exception

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        """save crash data into either the primary or deferred storage,
        depending on the deferral criteria"""
        if not self.config.deferral_criteria(raw_crash):
            self.primary_store.save_raw_crash(raw_crash, dumps, crash_id)
        else:
            self.deferred_store.save_raw_crash(raw_crash, dumps, crash_id)

    def save_processed(self, processed_crash):
        """save processed crash data into either the primary or deferred
        storage, depending on the deferral criteria"""
        if not self.config.deferral_criteria(processed_crash):
            self.primary_store.save_processed(processed_crash)
        else:
            self.deferred_store.save_processed(processed_crash)

    def get_raw_crash(self, crash_id):
        """get a raw crash 1st from primary and if not found then try the
        deferred.

        parameters:
           crash_id - the id of a raw crash to fetch"""
        try:
            return self.primary_store.get_raw_crash(crash_id)
        except CrashIDNotFound:
            return self.deferred_store.get_raw_crash(crash_id)

    def get_raw_dump(self, crash_id, name=None):
        """get a named crash dump 1st from primary and if not found then try
        the deferred.

        parameters:
           crash_id - the id of a dump to fetch
           name - name of the crash to fetch, or omit to fetch default crash"""
        try:
            return self.primary_store.get_raw_dump(crash_id, name)
        except CrashIDNotFound:
            return self.deferred_store.get_raw_dump(crash_id, name)

    def get_raw_dumps(self, crash_id):
        """get all crash dumps 1st from primary and if not found then try
        the deferred.

        parameters:
           crash_id - the id of a dump to fetch"""
        try:
            return self.primary_store.get_raw_dumps(crash_id)
        except CrashIDNotFound:
            return self.deferred_store.get_raw_dumps(crash_id)

    def get_raw_dumps_as_files(self, crash_id):
        """get all crash dump pathnames 1st from primary and if not found then
        try the deferred.

        parameters:
           crash_id - the id of a dump to fetch"""
        try:
            return self.primary_store.get_raw_dumps_as_files(crash_id)
        except CrashIDNotFound:
            return self.deferred_store.get_raw_dumps_as_files(crash_id)

    def get_unredacted_processed(self, crash_id):
        """fetch an unredacted processed_crash

        parameters:
           crash_id - the id of a processed_crash to fetch"""
        try:
            return self.primary_store.get_unredacted_processed(crash_id)
        except CrashIDNotFound:
            return self.deferred_store.get_unredacted_processed(crash_id)

    def remove(self, crash_id):
        """delete a crash from storage

        parameters:
           crash_id - the id of a crash to fetch"""
        try:
            self.primary_store.remove(crash_id)
        except CrashIDNotFound:
            self.deferred_store.remove(crash_id)

    def new_crashes(self):
        """return an iterator that yields a list of crash_ids of raw crashes
        that were added to the file system since the last time this iterator
        was requested."""
        return self.primary_store.new_crashes()


class PrimaryDeferredProcessedStorage(PrimaryDeferredStorage):
    """
    PrimaryDeferredProcessedStorage aggregates three methods of storage: it
    uses a deferral criteria predicate to decide where to store a raw crash,
    like PrimaryDeferredStorage -- but it stores all processed crashes in a
    third, separate storage.
    """
    required_config = Namespace()
    required_config.processed = Namespace()
    required_config.processed.add_option(
        'storage_class',
        doc='storage class for processed storage',
        default='',
        from_string_converter=class_converter
    )

    def __init__(self, config, quit_check_callback=None):
        super(PrimaryDeferredProcessedStorage, self).__init__(
            config,
            quit_check_callback
        )
        self.processed_store = config.processed.storage_class(
            config.processed,
            quit_check_callback
        )

    def save_processed(self, processed_crash):
        self.processed_store.save_processed(processed_crash)

    def get_unredacted_processed(self, crash_id):
        """fetch an unredacted processed crash from the underlying
        storage implementation"""
        return self.processed_store.get_unredacted_processed(crash_id)


class BenchmarkingCrashStorage(CrashStorageBase):
    """a wrapper around crash stores that will benchmark the calls in the logs
    """
    required_config = Namespace()
    required_config.add_option(
        name="benchmark_tag",
        doc="a tag to put on logged benchmarking lines",
        default='Benchmark',
    )
    required_config.add_option(
        name="wrapped_crashstore",
        doc="another crash store to be benchmarked",
        default='',
        from_string_converter=class_converter
    )

    def __init__(self, config, quit_check_callback=None):
        super(BenchmarkingCrashStorage, self).__init__(
            config,
            quit_check_callback
        )
        self.wrapped_crashstore = config.wrapped_crashstore(
            config,
            quit_check_callback)
        self.tag = config.benchmark_tag
        self.start_timer = datetime.datetime.now
        self.end_timer = datetime.datetime.now

    def close(self):
        """some implementations may need explicit closing."""
        self.wrapped_crashstore.close()

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        start_time = self.start_timer()
        self.wrapped_crashstore.save_raw_crash(raw_crash, dumps, crash_id)
        end_time = self.end_timer()
        self.config.logger.debug(
            '%s save_raw_crash %s',
            self.tag,
            end_time - start_time
        )

    def save_processed(self, processed_crash):
        start_time = self.start_timer()
        self.wrapped_crashstore.save_processed(processed_crash)
        end_time = self.end_timer()
        self.config.logger.debug(
            '%s save_processed %s',
            self.tag,
            end_time - start_time
        )

    def save_raw_and_processed(self, raw_crash, dumps, processed_crash,
                               crash_id):
        start_time = self.start_timer()
        self.wrapped_crashstore.save_raw_and_processed(
            raw_crash,
            dumps,
            processed_crash,
            crash_id
        )
        end_time = self.end_timer()
        self.config.logger.debug(
            '%s save_raw_and_processed %s',
            self.tag,
            end_time - start_time
        )

    def get_raw_crash(self, crash_id):
        start_time = self.start_timer()
        result = self.wrapped_crashstore.get_raw_crash(crash_id)
        end_time = self.end_timer()
        self.config.logger.debug(
            '%s get_raw_crash %s',
            self.tag,
            end_time - start_time
        )
        return result

    def get_raw_dump(self, crash_id, name=None):
        start_time = self.start_timer()
        result = self.wrapped_crashstore.get_raw_dump(crash_id)
        end_time = self.end_timer()
        self.config.logger.debug(
            '%s get_raw_dump %s',
            self.tag,
            end_time - start_time
        )
        return result

    def get_raw_dumps(self, crash_id):
        start_time = self.start_timer()
        result = self.wrapped_crashstore.get_raw_dumps(crash_id)
        end_time = self.end_timer()
        self.config.logger.debug(
            '%s get_raw_dumps %s',
            self.tag,
            end_time - start_time
        )
        return result

    def get_raw_dumps_as_files(self, crash_id):
        start_time = self.start_timer()
        result = self.wrapped_crashstore.get_raw_dumps_as_files(crash_id)
        end_time = self.end_timer()
        self.config.logger.debug(
            '%s get_raw_dumps_as_files %s',
            self.tag,
            end_time - start_time
        )
        return result

    def get_unredacted_processed(self, crash_id):
        start_time = self.start_timer()
        result = self.wrapped_crashstore.get_unredacted_processed(crash_id)
        end_time = self.end_timer()
        self.config.logger.debug(
            '%s get_unredacted_processed %s',
            self.tag,
            end_time - start_time
        )
        return result

    def remove(self, crash_id):
        start_time = self.start_timer()
        self.wrapped_crashstore.remove(crash_id)
        end_time = self.end_timer()
        self.config.logger.debug(
            '%s remove %s',
            self.tag,
            end_time - start_time
        )
