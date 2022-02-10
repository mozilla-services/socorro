# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/

import datetime
import json
import logging

from configman import Namespace
from configman.converters import class_converter
from configman.dotdict import DotDict
import json_schema_reducer

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    CrashIDNotFound,
    MemoryDumpsMapping,
)
from socorro.external.es.super_search_fields import SuperSearchFieldsData
from socorro.lib.ooid import date_from_ooid
from socorro.lib.util import dotdict_to_dict
from socorro.schemas import TELEMETRY_SOCORRO_CRASH_SCHEMA


LOGGER = logging.getLogger(__name__)


def wait_time_generator():
    yield from [1, 1, 1, 1, 1]


class CrashIDMissingDatestamp(Exception):
    """Indicates the crash id is invalid and missing a datestamp."""

    pass


def get_datestamp(crashid):
    """Parses out datestamp from a crashid.

    :returns: datetime

    :raises CrashIDMissingDatestamp: if the crash id has no datestamp at the end

    """
    datestamp = date_from_ooid(crashid)
    if datestamp is None:
        # We should never hit this situation unless the crashid is not valid
        raise CrashIDMissingDatestamp("%s is missing datestamp" % crashid)
    return datestamp


def build_keys(name_of_thing, crashid):
    """Builds a list of s3 pseudo-filenames

    When using keys for saving a crash, always use the first one given.

    When using keys for loading a crash, try each key in order. This lets us change our
    key scheme and continue to access things saved using the old key.

    :arg name_of_thing: the kind of thing we're building a filename for; e.g.
        "raw_crash"
    :arg crashid: the crash id for the thing being stored

    :returns: list of keys to try in order

    :raises CrashIDMissingDatestamp: if the crash id is missing a datestamp at the
        end

    """
    if name_of_thing == "raw_crash":
        # Insert the first 3 chars of the crashid providing some entropy
        # earlier in the key so that consecutive s3 requests get
        # distributed across multiple s3 partitions
        entropy = crashid[:3]
        date = get_datestamp(crashid).strftime("%Y%m%d")
        return [
            "v2/%(nameofthing)s/%(entropy)s/%(date)s/%(crashid)s"
            % {
                "nameofthing": name_of_thing,
                "entropy": entropy,
                "date": date,
                "crashid": crashid,
            }
        ]

    elif name_of_thing == "crash_report":
        # Crash data from the TelemetryBotoS3CrashStorage
        date = get_datestamp(crashid).strftime("%Y%m%d")
        return [
            "v1/%(nameofthing)s/%(date)s/%(crashid)s"
            % {"nameofthing": name_of_thing, "date": date, "crashid": crashid}
        ]

    return [
        "v1/%(nameofthing)s/%(crashid)s"
        % {"nameofthing": name_of_thing, "crashid": crashid}
    ]


class JSONISOEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        raise NotImplementedError(f"Don't know about {obj!r}")


def dict_to_str(a_mapping):
    if isinstance(a_mapping, DotDict):
        a_mapping = dotdict_to_dict(a_mapping)
    return json.dumps(a_mapping, cls=JSONISOEncoder)


def list_to_str(a_list):
    return json.dumps(list(a_list))


def str_to_list(a_string):
    return json.loads(a_string)


class BotoS3CrashStorage(CrashStorageBase):
    """Saves and loads crash data to S3"""

    required_config = Namespace()
    required_config.add_option(
        "resource_class",
        default="socorro.external.boto.connection_context.S3Connection",
        doc="fully qualified dotted Python classname to handle Boto connections",
        from_string_converter=class_converter,
        reference_value_from="resource.boto",
    )
    required_config.add_option(
        "temporary_file_system_storage_path",
        doc="a local filesystem path where dumps temporarily during processing",
        default="/home/socorro/temp",
        reference_value_from="resource.boto",
    )
    required_config.add_option(
        "dump_file_suffix",
        doc="the suffix used to identify a dump file (for use in temp files)",
        default=".dump",
        reference_value_from="resource.boto",
    )
    required_config.add_option(
        "json_object_hook",
        default="configman.dotdict.DotDict",
        from_string_converter=class_converter,
    )

    def __init__(self, config, namespace=""):
        super().__init__(config, namespace=namespace)
        self.conn = config.resource_class(config)

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        """Save raw crash data to S3 bucket.

        A raw crash consists of the raw crash annotations and all the dumps that came in
        the crash report. We need to save the raw crash file, a dump names file listing
        the dumps that came in the crash report, and then each of the dumps.

        """
        if dumps is None:
            dumps = MemoryDumpsMapping()

        path = build_keys("raw_crash", crash_id)[0]
        raw_crash_data = dict_to_str(raw_crash).encode("utf-8")
        self.conn.save_file(path, raw_crash_data)

        path = build_keys("dump_names", crash_id)[0]
        dump_names_data = list_to_str(dumps.keys()).encode("utf-8")
        self.conn.save_file(path, dump_names_data)

        # We don't know what type of dumps mapping we have. We do know,
        # however, that by calling the memory_dump_mapping method, we will get
        # a MemoryDumpMapping which is exactly what we need.
        dumps = dumps.as_memory_dumps_mapping()
        for dump_name, dump in dumps.items():
            if dump_name in (None, "", "upload_file_minidump"):
                dump_name = "dump"
            path = build_keys(dump_name, crash_id)[0]
            self.conn.save_file(path, dump)

    def save_processed_crash(self, raw_crash, processed_crash):
        """Save the processed crash file."""
        crash_id = processed_crash["uuid"]
        data = dict_to_str(processed_crash).encode("utf-8")
        path = build_keys("processed_crash", crash_id)[0]
        self.conn.save_file(path, data)

    def get_raw_crash(self, crash_id):
        """Get the raw crash file for the given crash id.

        :returns: DotDict

        :raises CrashIDNotFound: if the crash doesn't exist

        """
        try:
            path = build_keys("raw_crash", crash_id)[0]
            raw_crash_as_string = self.conn.load_file(path)
            return json.loads(
                raw_crash_as_string, object_hook=self.config.json_object_hook
            )
        except self.conn.KeyNotFound as x:
            raise CrashIDNotFound("%s not found: %s" % (crash_id, x))

    def get_raw_dump(self, crash_id, name=None):
        """Get a specified dump file for the given crash id.

        :returns: dump as bytes

        :raises CrashIDNotFound: if file does not exist

        """
        try:
            if name in (None, "", "upload_file_minidump"):
                name = "dump"
            path = build_keys(name, crash_id)[0]
            a_dump = self.conn.load_file(path)
            return a_dump
        except self.conn.KeyNotFound as x:
            raise CrashIDNotFound("%s not found: %s" % (crash_id, x))

    def get_dumps(self, crash_id):
        """Get all the dump files for a given crash id.

        :returns MemoryDumpsMapping:

        :raises CrashIDNotFound: if file does not exist

        """
        try:
            path = build_keys("dump_names", crash_id)[0]
            dump_names_as_string = self.conn.load_file(path)
            dump_names = str_to_list(dump_names_as_string)

            dumps = MemoryDumpsMapping()
            for dump_name in dump_names:
                if dump_name in (None, "", "upload_file_minidump"):
                    dump_name = "dump"
                path = build_keys(dump_name, crash_id)[0]
                dumps[dump_name] = self.conn.load_file(path)
            return dumps
        except self.conn.KeyNotFound as x:
            raise CrashIDNotFound("%s not found: %s" % (crash_id, x))

    def get_dumps_as_files(self, crash_id):
        """Get the dump files for given crash id and save them to tmp.

        :returns: dict of dumpname -> file path

        :raises CrashIDNotFound: if file does not exist

        """
        in_memory_dumps = self.get_dumps(crash_id)
        # convert our native memory dump mapping into a file dump mapping.
        return in_memory_dumps.as_file_dumps_mapping(
            crash_id,
            self.config.temporary_file_system_storage_path,
            self.config.dump_file_suffix,
        )

    def get_unredacted_processed(self, crash_id):
        """Get the processed crash.

        :returns: DotDict

        :raises CrashIDNotFound: if file does not exist

        """
        path = build_keys("processed_crash", crash_id)[0]
        try:
            processed_crash_as_string = self.conn.load_file(path)
            return json.loads(
                processed_crash_as_string, object_hook=self.config.json_object_hook
            )
        except self.conn.KeyNotFound as x:
            raise CrashIDNotFound("%s not found: %s" % (crash_id, x))


class TelemetryBotoS3CrashStorage(BotoS3CrashStorage):
    """Sends a subset of the processed crash to an S3 bucket

    The subset of the processed crash is based on the JSON Schema which is
    derived from "socorro/external/es/super_search_fields.py".

    """

    def __init__(self, config, *args, **kwargs):
        super().__init__(config, *args, **kwargs)
        self._all_fields = SuperSearchFieldsData().get()

    def save_processed_crash(self, raw_crash, processed_crash):
        """Save processed crash data.

        For Telemetry, we combine the raw and processed crash data into a "crash report"
        which we save to an S3 bucket for the Telemetry system to pick up later.

        """
        crash_report = {}

        # TODO Opportunity of optimization: We could inspect
        # TELEMETRY_SOCORRO_CRASH_SCHEMA and get a list of all (recursive) keys that are
        # in there and use that to limit the two following loops to not bother filling
        # up `crash_report` with keys that will never be needed.

        # FIXME(willkg): once we've moved all the raw crash stuff into the processed
        # crash, we can rework this to just look at the processed crash and reduce it by
        # the schema

        # Rename fields in raw_crash
        raw_fields_map = {
            x["in_database_name"]: x["name"]
            for x in self._all_fields.values()
            if x["namespace"] == "raw_crash"
        }
        for key, val in raw_crash.items():
            crash_report[raw_fields_map.get(key, key)] = val

        # Rename fields in processed_crash
        processed_fields_map = {
            x["in_database_name"]: x["name"]
            for x in self._all_fields.values()
            if x["namespace"] == "processed_crash"
        }
        for key, val in processed_crash.items():
            crash_report[processed_fields_map.get(key, key)] = val

        # Validate crash_report
        crash_report = json_schema_reducer.make_reduced_dict(
            TELEMETRY_SOCORRO_CRASH_SCHEMA, crash_report
        )

        crash_id = crash_report["uuid"]
        data = dict_to_str(crash_report).encode("utf-8")
        path = build_keys("crash_report", crash_id)[0]
        self.conn.save_file(path, data)

    def get_unredacted_processed(self, crash_id):
        """Get a crash report from the S3 bucket.

        :returns: DotDict

        :raises CrashIDNotFound: if file does not exist

        """
        path = build_keys("crash_report", crash_id)[0]
        try:
            crash_report_as_str = self.conn.load_file(path)
            return json.loads(
                crash_report_as_str, object_hook=self.config.json_object_hook
            )
        except self.conn.KeyNotFound as x:
            raise CrashIDNotFound("%s not found: %s" % (crash_id, x))
