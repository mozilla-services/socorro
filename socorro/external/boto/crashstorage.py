# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
import json
import logging

from configman import Namespace
from configman.converters import class_converter

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    CrashIDNotFound,
    MemoryDumpsMapping,
    migrate_raw_crash,
)
from socorro.lib.libjsonschema import JsonSchemaReducer
from socorro.lib.libsocorrodataschema import (
    get_schema,
    permissions_transform_function,
    SocorroDataReducer,
    transform_schema,
)
from socorro.lib.libooid import date_from_ooid
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
            "v1/%(nameofthing)s/%(date)s/%(crashid)s"
            % {
                "nameofthing": name_of_thing,
                "date": date,
                "crashid": crashid,
            },
            # NOTE(willkg): This format is deprecated and will be removed in April 2023
            "v2/%(nameofthing)s/%(entropy)s/%(date)s/%(crashid)s"
            % {
                "nameofthing": name_of_thing,
                "entropy": entropy,
                "date": date,
                "crashid": crashid,
            },
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
        "dump_file_suffix",
        doc="the suffix used to identify a dump file (for use in temp files)",
        default=".dump",
        reference_value_from="resource.boto",
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
        """Get the raw crash file for the given crash id

        :returns: dict

        :raises CrashIDNotFound: if the crash doesn't exist

        """
        for path in build_keys("raw_crash", crash_id):
            try:
                raw_crash_as_string = self.conn.load_file(path)
                data = json.loads(raw_crash_as_string)
                return migrate_raw_crash(data)
            except self.conn.KeyNotFound:
                continue

        raise CrashIDNotFound("%s not found" % crash_id)

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

    def get_dumps_as_files(self, crash_id, tmpdir):
        """Get the dump files for given crash id and save them to tmp.

        :returns: dict of dumpname -> file path

        :raises CrashIDNotFound: if file does not exist

        """
        in_memory_dumps = self.get_dumps(crash_id)
        # convert our native memory dump mapping into a file dump mapping.
        return in_memory_dumps.as_file_dumps_mapping(
            crash_id,
            tmpdir,
            self.config.dump_file_suffix,
        )

    def get_processed(self, crash_id):
        """Get the processed crash.

        :returns: dict

        :raises CrashIDNotFound: if file does not exist

        """
        path = build_keys("processed_crash", crash_id)[0]
        try:
            processed_crash_as_string = self.conn.load_file(path)
            return json.loads(processed_crash_as_string)
        except self.conn.KeyNotFound as x:
            raise CrashIDNotFound("%s not found: %s" % (crash_id, x))


class TelemetryBotoS3CrashStorage(BotoS3CrashStorage):
    """Sends a subset of the processed crash to an S3 bucket

    The subset of the processed crash is based on the JSON Schema which is
    derived from "socorro/external/es/super_search_fields.py".

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Create a reducer that traverses documents and reduces them down to the
        # structure of the specified schema
        self.build_reducers()

    def build_reducers(self):
        processed_crash_schema = get_schema("processed_crash.schema.yaml")
        only_public = permissions_transform_function(
            permissions_have=["public"],
            default_permissions=processed_crash_schema["default_permissions"],
        )
        public_processed_crash_schema = transform_schema(
            schema=processed_crash_schema,
            transform_function=only_public,
        )
        self.processed_crash_reducer = SocorroDataReducer(
            schema=public_processed_crash_schema
        )

        self.telemetry_reducer = JsonSchemaReducer(
            schema=TELEMETRY_SOCORRO_CRASH_SCHEMA
        )

    # List of source -> target keys which have different names for historical reasons
    HISTORICAL_MANUAL_KEYS = [
        # processed crash source key, crash report target key
        ("build", "build_id"),
        ("date_processed", "date"),
        ("os_pretty_version", "platform_pretty_version"),
        ("os_name", "platform"),
        ("os_version", "platform_version"),
    ]

    def save_processed_crash(self, raw_crash, processed_crash):
        """Save processed crash data.

        For Telemetry, we reduce the processed crash into a crash report that matches
        the telemetry_socorro_crash.json schema.

        For historical reasons, we then add some additional fields manually.

        """
        # Reduce processed crash to public-only fields
        public_data = self.processed_crash_reducer.traverse(document=processed_crash)

        # Reduce public processed_crash to telemetry schema fields
        telemetry_data = self.telemetry_reducer.traverse(document=public_data)

        # Add additional fields that have different names for historical reasons
        for source_key, target_key in self.HISTORICAL_MANUAL_KEYS:
            if source_key in public_data:
                telemetry_data[target_key] = public_data[source_key]

        crash_id = telemetry_data["uuid"]
        data = dict_to_str(telemetry_data).encode("utf-8")
        path = build_keys("crash_report", crash_id)[0]
        self.conn.save_file(path, data)

    def get_processed(self, crash_id):
        """Get a crash report from the S3 bucket.

        :returns: dict

        :raises CrashIDNotFound: if file does not exist

        """
        path = build_keys("crash_report", crash_id)[0]
        try:
            crash_report_as_str = self.conn.load_file(path)
            return json.loads(crash_report_as_str)
        except self.conn.KeyNotFound as x:
            raise CrashIDNotFound("%s not found: %s" % (crash_id, x))
