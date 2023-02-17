# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Base classes for crashstorage system."""

from contextlib import suppress
import logging
import os


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


class CrashIDNotFound(Exception):
    pass


def migrate_raw_crash(data):
    """Migrates the raw crash structure to the current structure

    Currently, the version is 2.

    :arg data: the raw crash structure as saved

    :returns: the migrated raw crash structure

    """
    if "version" not in data:
        # If it has no version, then it's version 1
        data["version"] = 1

    if data["version"] == 1:
        # Convert to version 2 by moving some keys to a new metadata section, deleting
        # the old location, and updating to version 2
        old_keys = [
            "collector_notes",
            "dump_checksums",
            "payload",
            "payload_compressed",
        ]
        metadata = data.get("metadata", {})
        metadata.update(
            {
                "collector_notes": data.get("collector_notes", []),
                "dump_checksums": data.get("dump_checksums", {}),
                "payload_compressed": data.get("payload_compressed", "0"),
                "payload": data.get("payload", "unknown"),
                "migrated_from_version_1": True,
            }
        )
        data["metadata"] = metadata
        for key in old_keys:
            if key in data:
                del data[key]
        data["version"] = 2

    return data


class CrashStorageBase:
    """Base class for all crash storage classes."""

    def __init__(self):
        # Collection of non-fatal exceptions that can be raised by a given storage
        # implementation. This may be fetched by a client of the crashstorge so that it
        # can determine if it can try a failed storage operation again.
        self.exceptions_eligible_for_retry = ()
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)

    def close(self):
        """Close resources used by this crashstorage."""

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        """Save raw crash data.

        :param raw_crash: Mapping containing the raw crash meta data. It is often saved
            as a json file, but here it is in the form of a dict.
        :param dumps: A dict of dump name keys and binary blob values.
        :param crash_id: the crash report id

        """

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

        :returns: dict of raw crash data

        :raises CrashIdNotFound:

        """
        raise NotImplementedError("get_raw_crash is not implemented")

    def get_raw_dump(self, crash_id, name):
        """Fetch dump for a raw crash

        :param crash_id: crash report id
        :param name: name of dump to fetch

        :returns: dump as bytes

        :raises CrashIdNotFound:

        """
        raise NotImplementedError("get_raw_dump is not implemented")

    def get_dumps(self, crash_id):
        """Fetch all dumps for a crash report

        :param crash_id: crash report id

        :returns: MemoryDumpsMapping of dumps

        :raises CrashIdNotFound:

        """
        raise NotImplementedError("get_dumps is not implemented")

    def get_dumps_as_files(self, crash_id, tmpdir):
        """Fetch all dumps for a crash report and save as files.

        :param crash_id: crash report id
        :param tmpdir: the path to store the dump files in

        :returns: dict of dumpname -> file path

        :raises CrashIdNotFound:

        """
        raise NotImplementedError("get_dumps_as_files is not implemented")

    def get_processed_crash(self, crash_id):
        """Fetch processed crash.

        :arg crash_id: crash report id

        :returns: dict of processed crash data

        :raises CrashIdNotFound:

        """
        raise NotImplementedError("get_processed_crash is not implemented")

    def remove(self, crash_id):
        """Delete crash report data from storage

        :param crash_id: crash report id

        """
        raise NotImplementedError("remove is not implemented")


class InMemoryCrashStorage(CrashStorageBase):
    """In-memory crash storage for testing."""

    def __init__(self):
        # crash id -> data
        self._raw_crash_data = {}
        # crash id -> (dump name -> data)
        self._dumps = {}
        # crash id -> data
        self._processed_crash_data = {}

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        self._raw_crash_data[crash_id] = raw_crash
        self._dumps[crash_id] = MemoryDumpsMapping(dumps)

    def save_processed_crash(self, raw_crash, processed_crash):
        crash_id = processed_crash["uuid"]
        self._processed_crash_data[crash_id] = processed_crash

    def get_raw_crash(self, crash_id):
        try:
            return self._raw_crash_data[crash_id]
        except KeyError:
            raise CrashIDNotFound(f"{crash_id} not found")

    def get_raw_dump(self, crash_id, name):
        try:
            return self._dumps[crash_id][name]
        except KeyError:
            raise CrashIDNotFound(f"{crash_id} not found")

    def get_dumps(self, crash_id):
        try:
            return self._dumps[crash_id]
        except KeyError:
            raise CrashIDNotFound(f"{crash_id} not found")

    def get_dumps_as_files(self, crash_id, tmpdir):
        try:
            return self._dumps[crash_id].as_file_dumps_mapping(
                crash_id=crash_id,
                temp_path=str(tmpdir),
                dump_file_suffix=".dump",
            )
        except KeyError:
            raise CrashIDNotFound(f"{crash_id} not found")

    def get_processed_crash(self, crash_id):
        try:
            return self._processed_crash_data[crash_id]
        except KeyError:
            raise CrashIDNotFound(f"{crash_id} not found")

    def remove(self, crash_id):
        with suppress(KeyError):
            del self._raw_crash_data[crash_id]

        with suppress(KeyError):
            del self._dumps[crash_id]

        with suppress(KeyError):
            del self._processed_crash_data[crash_id]
