# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Base classes for crashstorage system."""

import datetime
import collections
import logging
import os
import sys

from configman import Namespace, RequiredConfig
from configman.converters import class_converter, str_to_list
from configman.dotdict import DotDict
import markus


class MemoryDumpsMapping(dict):
    """there has been a bifurcation in the crash storage data throughout the
    history of the classes.  The crash dumps have two different
    representations:

    1. a mapping of crash names to binary data blobs
    2. a mapping of crash names to file pathnames

    It has been a manner of gentleman's agreement that two types do not mix.
    However, as the two methods have evolved in parallel the distinction has
    become more and more inconvenient.

    This class represents case 1 from above. It is a mapping of crash dump
    names to binary representation of the dump. Before using a mapping, a given
    crash store should call the "as_file_dumps_mapping" or
    "as_memory_dumps_mapping" depend on what that crashstorage implementation
    is going to need.

    """

    def as_file_dumps_mapping(self, crash_id, temp_path, dump_file_suffix):
        """convert this MemoryDumpMapping into a FileDumpsMappng by writing
        each of the dump to a filesystem."""
        name_to_pathname_mapping = FileDumpsMapping()
        for a_dump_name, a_dump in self.items():
            if a_dump_name in (None, "", "dump"):
                a_dump_name = "upload_file_minidump"
            dump_pathname = os.path.join(
                temp_path,
                "%s.%s.TEMPORARY%s" % (crash_id, a_dump_name, dump_file_suffix),
            )
            name_to_pathname_mapping[a_dump_name] = dump_pathname
            with open(dump_pathname, "wb") as f:
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

    1. a mapping of crash names to binary data blobs
    2. a mapping of crash names to file pathnames.

    It has been a manner of gentleman's agreement that two types do not mix.
    However, as the two methods have evolved in parallel the distinction has
    become more and more inconvenient.


    This class represents case 2 from above.  It is a mapping of crash dump
    names to pathname of a file containing the dump.  Before using a mapping,
    a given crash store should call the "as_file_dumps_mapping" or
    "as_memory_dumps_mapping" depend on what that crashstorage implementation
    is going to need.

    """

    def as_file_dumps_mapping(self, *args, **kwargs):
        """this crash is already a FileDumpsMapping, so we can just return self.
        However, the arguments to this function are ignored.  The purpose of
        this class is not to move crashes around on filesytem. The arguments
        a solely for maintaining a consistent interface with the companion
        MemoryDumpsMapping class."""
        return self

    def as_memory_dumps_mapping(self):
        """Convert this into a MemoryDumpsMapping by opening and reading each
        of the dumps in the mapping."""
        in_memory_dumps = MemoryDumpsMapping()
        for dump_key, dump_path in self.items():
            with open(dump_path, "rb") as f:
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
        name="forbidden_keys",
        doc="a list of keys not allowed in a redacted processed crash",
        default=(
            "url, email, exploitability,"
            "json_dump.sensitive,"
            "upload_file_minidump_flash1.json_dump.sensitive,"
            "upload_file_minidump_flash2.json_dump.sensitive,"
            "upload_file_minidump_browser.json_dump.sensitive,"
            "memory_info"
        ),
        reference_value_from="resource.redactor",
    )

    def __init__(self, config):
        self.config = config
        self.forbidden_keys = [x.strip() for x in self.config.forbidden_keys.split(",")]

    def redact(self, a_mapping):
        """this is the function that does the redaction."""
        for a_key in self.forbidden_keys:
            sub_mapping = a_mapping
            sub_keys = a_key.split(".")
            try:
                for a_sub_key in sub_keys[:-1]:  # step through the subkeys
                    sub_mapping = sub_mapping[a_sub_key.strip()]
                del sub_mapping[sub_keys[-1]]
            except (AttributeError, KeyError):
                # this is okay, our key was already deleted by
                # another pattern that matched at a higher level
                pass

    def __call__(self, a_mapping):
        self.redact(a_mapping)


class CrashIDNotFound(Exception):
    pass


class CrashStorageBase(RequiredConfig):
    """Base class for all crash storage classes."""

    required_config = Namespace()
    required_config.add_option(
        name="redactor_class",
        doc="the name of the class that implements a 'redact' method",
        default=Redactor,
        reference_value_from="resource.redactor",
    )

    def __init__(self, config, namespace=""):
        """Initializer

        :param config: configman DotDict holding configuration information
        :param namespace: namespace for this crashstorage instance; used
            for metrics prefixes and logging

        """
        self.config = config
        self.namespace = namespace

        # Collection of non-fatal exceptions that can be raised by a given storage
        # implementation. This may be fetched by a client of the crashstorge so that it
        # can determine if it can try a failed storage operation again.
        self.exceptions_eligible_for_retry = ()
        self.redactor = config.redactor_class(config)
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)

    def close(self):
        """Close resources used by this crashstorage."""
        pass

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        """Save raw crash data.

        :param raw_crash: Mapping containing the raw crash meta data. It is often saved
            as a json file, but here it is in the form of a dict.
        :param dumps: A dict of dump name keys and binary blob values.
        :param crash_id: the crash report id

        """
        pass

    def save_processed_crash(self, raw_crash, processed_crash):
        """Save processed crash to crash storage

        Saves a processed crash to crash storage. This includes the raw crash
        data in case the crash storage combines the two.

        :param raw_crash: the raw crash data (no dumps)
        :param processed_crash: the processed crash data

        """
        raise NotImplementedError("save_processed_crash not implemented")

    def get_raw_crash(self, crash_id):
        """Fetch raw crash

        :param crash_id: crash report id for data to fetch

        :returns: DotDict of raw crash data

        """
        raise NotImplementedError("get_raw_crash is not implemented")

    def get_raw_dump(self, crash_id, name=None):
        """Fetch dump for a raw crash

        :param crash_id: crash report id
        :param name: name of dump to fetch

        :returns: dump as bytes

        """
        raise NotImplementedError("get_raw_dump is not implemented")

    def get_raw_dumps(self, crash_id):
        """Fetch all dumps for a crash report

        :param crash_id: crash report id

        :returns: MemoryDumpsMapping of dumps

        """
        raise NotImplementedError("get_raw_dumps is not implemented")

    def get_raw_dumps_as_files(self, crash_id):
        """Fetch all dumps for a crash report and save as files.

        :param crash_id: crash report id

        :returns: dict of dumpname -> file path

        """
        raise NotImplementedError("get_raw_dumps is not implemented")

    def get_processed(self, crash_id):
        """Fetch processed crash.

        :arg crash_id: crash report id

        :returns: DotDict

        """
        processed_crash = self.get_unredacted_processed(crash_id)
        self.redactor(processed_crash)
        return processed_crash

    def get_unredacted_processed(self, crash_id):
        """Fetch processed crash with no redaction

        :param crash_id: crash report id

        :returns: DotDict

        """
        raise NotImplementedError("get_unredacted_processed is not implemented")

    def remove(self, crash_id):
        """Delete crash report data from storage

        :param crash_id: crash report id

        """
        raise NotImplementedError("remove is not implemented")


class PolyStorageError(Exception, collections.MutableSequence):
    """Exception container holding a sequence of exceptions with tracebacks

    :arg message: an optional over all error message

    """

    def __init__(self, *args):
        super().__init__(*args)
        self.exceptions = []  # the collection

    def gather_current_exception(self):
        """Append the currently active exception to the collection"""
        self.exceptions.append(sys.exc_info())

    def has_exceptions(self):
        """Boolean opposite of is_empty"""
        return bool(self.exceptions)

    def __len__(self):
        """Length of exception collection"""
        return len(self.exceptions)

    def __iter__(self):
        """Start an iterator over the sequence"""
        return iter(self.exceptions)

    def __contains__(self, value):
        """Search the sequence for a value and return true if it is present"""
        return self.exceptions.__contains__(value)

    def __getitem__(self, index):
        """Get a specific exception by index"""
        return self.exceptions.__getitem__(index)

    def __setitem__(self, index, value):
        """Set the value for an index in the sequence"""
        self.exceptions.__setitem__(index, value)

    def __str__(self):
        output = []
        if self.args:
            output.append(self.args[0])
        for e in self.exceptions:
            output.append(repr(e[1]))
        return ",".join(output)


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
                "crashstorage_class", from_string_converter=class_converter
            )

    def __len__(self):
        return len(self.storage_namespaces)

    def __getitem__(self, key):
        return self.storage_namespaces[key]

    def __repr__(self):
        return "StorageNamespaceList(%s)" % repr(self.storage_namespaces)

    @classmethod
    def converter(cls, storage_namespace_list_str):
        """from_string_converter-compatible factory method.

        parameters:
            storage_namespace_list_str - comma-separated list of config
                namespaces containing info about crash storages.
        """
        namespaces = [name.strip() for name in storage_namespace_list_str.split(",")]
        return cls(namespaces)


class PolyCrashStorage(CrashStorageBase):
    """Crashstorage pipeline for multiple crashstorage destinations

    This class is useful for "save" operations only--it does not implement the "get"
    operations.

    The contained crashstorage instances are specified in the configuration.  Each key
    in the ``storage_namespaces`` config option will be used to create a crashstorage
    instance that this saves to. The keys are namespaces in the config, and any options
    defined under those namespaces will be isolated within the config passed to the
    crashstorage instance. For example:

    .. code-block:: ini
        destination.crashstorage_namespaces=postgres,s3

        destination.postgres.crashstorage_class=module.path.PostgresStorage
        destination.postgres.my.config=Postgres

        destination.s3.crashstorage_class=module.path.S3Storage
        destination.s3.my.config=S3

    With this config, there are two crashstorage instances this class will create: one
    for Postgres, and one for S3. The PostgresStorage instance will see the
    ``my.config`` option as being set to "Postgres", while the S3Storage instance will
    see ``my.config`` set to "S3".

    """

    required_config = Namespace()
    required_config.add_option(
        "storage_namespaces",
        doc="a comma delimited list of storage namespaces",
        default="",
        from_string_converter=StorageNamespaceList.converter,
        likely_to_be_changed=True,
    )

    def __init__(self, config, namespace=""):
        """Instantiate all the subordinate crashstorage instances

        :param config: configman DotDict holding configuration information
        :param namespace: namespace for this crashstorage instance; used
            for metrics prefixes and logging

        """
        super().__init__(config, namespace)
        # The list of the namespaces in which the subordinate instances are stored.
        self.storage_namespaces = config.storage_namespaces
        # Instances of the subordinate crash stores.
        self.stores = DotDict()
        for storage_namespace in self.storage_namespaces:
            absolute_namespace = ".".join(
                x for x in [namespace, storage_namespace] if x
            )
            self.stores[storage_namespace] = config[
                storage_namespace
            ].crashstorage_class(
                config[storage_namespace], namespace=absolute_namespace,
            )

    def close(self):
        """Close resources used by crashstorage instances.

        :raises PolyStorageError: An exception container holding a list of the
            exceptions raised by the subordinate storage
            systems.

        """
        storage_exception = PolyStorageError()
        for a_store in self.stores.values():
            try:
                a_store.close()
            except Exception as x:
                self.logger.error("%s failure: %s", a_store.__class__, str(x))
                storage_exception.gather_current_exception()
        if storage_exception.has_exceptions():
            raise storage_exception

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        """Save raw crash to all crashstorage destinations.

        :param raw_crash: the raw crash data
        :param dumps: mapping of dump name keys -> dump binary
        :param crash_id: the crash report id

        """
        storage_exception = PolyStorageError()
        for a_store in self.stores.values():
            try:
                a_store.save_raw_crash(raw_crash, dumps, crash_id)
            except Exception as x:
                self.logger.error("%s failure: %s", a_store.__class__, str(x))
                storage_exception.gather_current_exception()
        if storage_exception.has_exceptions():
            raise storage_exception

    def save_processed_crash(self, raw_crash, processed_crash):
        """Save processed crash to all crashstorage destinations

        :param raw_crash: the raw crash data
        :param processed_crash: the processed crash data

        NOTE(willkg): Crash storage systems that implement this should
        not mutate the raw and processed crash structures!

        """
        storage_exception = PolyStorageError()
        for a_store in self.stores.values():
            try:
                a_store.save_processed_crash(raw_crash, processed_crash)
            except Exception:
                store_class = getattr(a_store, "wrapped_object", a_store.__class__)
                crash_id = processed_crash.get("uuid", "NONE")
                self.logger.error(
                    "%r failed (crash id: %s)", store_class, crash_id, exc_info=True
                )
                storage_exception.gather_current_exception()
        if storage_exception.has_exceptions():
            raise storage_exception


class BenchmarkingCrashStorage(CrashStorageBase):
    """Wrapper around crash stores that will benchmark the calls in the logs"""

    required_config = Namespace()
    required_config.add_option(
        name="benchmark_tag",
        doc="a tag to put on logged benchmarking lines",
        default="Benchmark",
    )
    required_config.add_option(
        name="wrapped_crashstore",
        doc="another crash store to be benchmarked",
        default="",
        from_string_converter=class_converter,
    )

    def __init__(self, config, namespace=""):
        super().__init__(config, namespace=namespace)
        self.wrapped_crashstore = config.wrapped_crashstore(config, namespace=namespace)
        self.tag = config.benchmark_tag
        self.start_timer = datetime.datetime.now
        self.end_timer = datetime.datetime.now
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)

    def close(self):
        """some implementations may need explicit closing."""
        self.wrapped_crashstore.close()

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        start_time = self.start_timer()
        self.wrapped_crashstore.save_raw_crash(raw_crash, dumps, crash_id)
        end_time = self.end_timer()
        self.logger.debug("%s save_raw_crash %s", self.tag, end_time - start_time)

    def save_processed_crash(self, raw_crash, processed_crash):
        start_time = self.start_timer()
        self.wrapped_crashstore.save_processed_crash(raw_crash, processed_crash)
        end_time = self.end_timer()
        self.logger.debug("%s save_processed_crash %s", self.tag, end_time - start_time)

    def get_raw_crash(self, crash_id):
        start_time = self.start_timer()
        result = self.wrapped_crashstore.get_raw_crash(crash_id)
        end_time = self.end_timer()
        self.logger.debug("%s get_raw_crash %s", self.tag, end_time - start_time)
        return result

    def get_raw_dump(self, crash_id, name=None):
        start_time = self.start_timer()
        result = self.wrapped_crashstore.get_raw_dump(crash_id)
        end_time = self.end_timer()
        self.logger.debug("%s get_raw_dump %s", self.tag, end_time - start_time)
        return result

    def get_raw_dumps(self, crash_id):
        start_time = self.start_timer()
        result = self.wrapped_crashstore.get_raw_dumps(crash_id)
        end_time = self.end_timer()
        self.logger.debug("%s get_raw_dumps %s", self.tag, end_time - start_time)
        return result

    def get_raw_dumps_as_files(self, crash_id):
        start_time = self.start_timer()
        result = self.wrapped_crashstore.get_raw_dumps_as_files(crash_id)
        end_time = self.end_timer()
        self.logger.debug(
            "%s get_raw_dumps_as_files %s", self.tag, end_time - start_time
        )
        return result

    def get_unredacted_processed(self, crash_id):
        start_time = self.start_timer()
        result = self.wrapped_crashstore.get_unredacted_processed(crash_id)
        end_time = self.end_timer()
        self.logger.debug(
            "%s get_unredacted_processed %s", self.tag, end_time - start_time
        )
        return result

    def remove(self, crash_id):
        start_time = self.start_timer()
        self.wrapped_crashstore.remove(crash_id)
        end_time = self.end_timer()
        self.logger.debug("%s remove %s", self.tag, end_time - start_time)


class MetricsEnabledBase(RequiredConfig):
    """Base class for capturing metrics for crashstorage classes"""

    required_config = Namespace()
    required_config.add_option(
        "metrics_prefix",
        doc="a string to be used as the prefix for metrics keys",
        default="",
    )
    required_config.add_option(
        "active_list",
        default="save_processed_crash,act",
        doc="a comma delimeted list of counters that are enabled",
        from_string_converter=str_to_list,
    )

    def __init__(self, config, namespace=""):
        self.config = config
        self.metrics = markus.get_metrics(self.config.metrics_prefix)

    def _make_key(self, *args):
        return ".".join(x for x in args if x)


class MetricsCounter(MetricsEnabledBase):
    """Counts the number of times it's called"""

    required_config = Namespace()

    def __getattr__(self, attr):
        if attr in self.config.active_list:
            self.metrics.incr(attr)
        return self._noop

    def _noop(self, *args, **kwargs):
        pass


class MetricsBenchmarkingWrapper(MetricsEnabledBase):
    """Sends timings for specified method calls in wrapped crash store"""

    required_config = Namespace()
    required_config.add_option(
        name="wrapped_object_class",
        doc="fully qualified Python class path for an object to an be benchmarked",
        default="",
        from_string_converter=class_converter,
    )

    def __init__(self, config, namespace=""):
        super().__init__(config, namespace=namespace)
        self.wrapped_object = config.wrapped_object_class(config, namespace=namespace)

    def close(self):
        self.wrapped_object.close()

    def __getattr__(self, attr):
        wrapped_attr = getattr(self.wrapped_object, attr)
        if attr in self.config.active_list:

            def benchmarker(*args, **kwargs):
                metrics_key = self._make_key(
                    self.config.wrapped_object_class.__name__, attr
                )
                with self.metrics.timer(metrics_key):
                    return wrapped_attr(*args, **kwargs)

            return benchmarker
        return wrapped_attr
