# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import logging

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    CrashIDNotFound,
    MemoryDumpsMapping,
    get_datestamp,
    dict_to_str,
    list_to_str,
    str_to_list,
)
from socorro.external.boto.connection_context import S3Connection
from socorro.lib.libjsonschema import JsonSchemaReducer
from socorro.lib.libsocorrodataschema import (
    get_schema,
    permissions_transform_function,
    SocorroDataReducer,
    transform_schema,
)
from socorro.schemas import TELEMETRY_SOCORRO_CRASH_SCHEMA


LOGGER = logging.getLogger(__name__)


def wait_time_generator():
    yield from [1, 1, 1, 1, 1]


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
        date = get_datestamp(crashid).strftime("%Y%m%d")
        return [f"v1/{name_of_thing}/{date}/{crashid}"]

    elif name_of_thing == "crash_report":
        # Crash data from the TelemetryBotoS3CrashStorage
        date = get_datestamp(crashid).strftime("%Y%m%d")
        return [f"v1/{name_of_thing}/{date}/{crashid}"]

    return [f"v1/{name_of_thing}/{crashid}"]


class BotoS3CrashStorage(CrashStorageBase):
    """Saves and loads crash data to S3"""

    def __init__(
        self,
        bucket="crashstats",
        dump_file_suffix=".dump",
        metrics_prefix="processor.s3",
        region=None,
        access_key=None,
        secret_access_key=None,
        endpoint_url=None,
    ):
        """
        :arg bucket: the S3 bucket to save to
        :arg dump_file_suffix: the suffix used to identify a dump file (for use in temp
            files)
        :arg region: the AWS region to use
        :arg access_key: the AWS access_key to use
        :arg secret_access_key: the AWS secret_access_key to use
        :arg endpoint_url: the endpoint url to use when in a local development
            environment

        """
        super().__init__()
        self.connection = self.build_connection(
            region=region,
            access_key=access_key,
            secret_access_key=secret_access_key,
            endpoint_url=endpoint_url,
        )
        self.bucket = bucket
        self.dump_file_suffix = dump_file_suffix

    @classmethod
    def build_connection(cls, region, access_key, secret_access_key, endpoint_url):
        """
        :arg region: the S3 region to use
        :arg access_key: the S3 access_key to use
        :arg secret_access_key: the S3 secret_access_key to use
        :arg endpoint_url: the endpoint url to use when in a local development
            environment

        """
        return S3Connection(
            region=region,
            access_key=access_key,
            secret_access_key=secret_access_key,
            endpoint_url=endpoint_url,
        )

    def load_file(self, path):
        return self.connection.load_file(self.bucket, path)

    def save_file(self, path, data):
        return self.connection.save_file(self.bucket, path, data)

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
        self.save_file(path, raw_crash_data)

        path = build_keys("dump_names", crash_id)[0]
        dump_names_data = list_to_str(dumps.keys()).encode("utf-8")
        self.save_file(path, dump_names_data)

        # We don't know what type of dumps mapping we have. We do know,
        # however, that by calling the memory_dump_mapping method, we will get
        # a MemoryDumpMapping which is exactly what we need.
        dumps = dumps.as_memory_dumps_mapping()
        for dump_name, dump in dumps.items():
            if dump_name in (None, "", "upload_file_minidump"):
                dump_name = "dump"
            path = build_keys(dump_name, crash_id)[0]
            self.save_file(path, dump)

    def save_processed_crash(self, raw_crash, processed_crash):
        """Save the processed crash file."""
        crash_id = processed_crash["uuid"]
        data = dict_to_str(processed_crash).encode("utf-8")
        path = build_keys("processed_crash", crash_id)[0]
        self.save_file(path, data)

    def list_objects_paginator(self, prefix, page_size=None):
        """Yield pages of object keys in the bucket that have a specified key prefix

        :arg prefix: the prefix to look at
        :arg page_size: the number of results to return per page

        :returns: generator of pages (lists) of object keys
        """
        for page in self.connection.list_objects_paginator(
            bucket=self.bucket, prefix=prefix, page_size=page_size
        ):
            yield [item["Key"] for item in page.get("Contents", [])]

    def exists_object(self, key):
        """Returns whether the object exists in the bucket

        :arg key: the key to check

        :returns: bool

        """
        try:
            self.connection.head_object(bucket=self.bucket, key=key)
            return True
        except self.connection.KeyNotFound:
            return False

    def get_raw_crash(self, crash_id):
        """Get the raw crash file for the given crash id

        :returns: dict

        :raises CrashIDNotFound: if the crash doesn't exist

        """
        for path in build_keys("raw_crash", crash_id):
            try:
                raw_crash_as_string = self.load_file(path)
                data = json.loads(raw_crash_as_string)
                return data
            except self.connection.KeyNotFound:
                continue

        raise CrashIDNotFound(f"{crash_id} not found")

    def get_raw_dump(self, crash_id, name=None):
        """Get a specified dump file for the given crash id.

        :returns: dump as bytes

        :raises CrashIDNotFound: if file does not exist

        """
        try:
            if name in (None, "", "upload_file_minidump"):
                name = "dump"
            path = build_keys(name, crash_id)[0]
            a_dump = self.load_file(path)
            return a_dump
        except self.connection.KeyNotFound as exc:
            raise CrashIDNotFound(f"{crash_id} not found: {exc}") from exc

    def get_dumps(self, crash_id):
        """Get all the dump files for a given crash id.

        :returns MemoryDumpsMapping:

        :raises CrashIDNotFound: if file does not exist

        """
        try:
            path = build_keys("dump_names", crash_id)[0]
            dump_names_as_string = self.load_file(path)
            dump_names = str_to_list(dump_names_as_string)

            dumps = MemoryDumpsMapping()
            for dump_name in dump_names:
                if dump_name in (None, "", "upload_file_minidump"):
                    dump_name = "dump"
                path = build_keys(dump_name, crash_id)[0]
                dumps[dump_name] = self.load_file(path)
            return dumps
        except self.connection.KeyNotFound as exc:
            raise CrashIDNotFound(f"{crash_id} not found: {exc}") from exc

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
            self.dump_file_suffix,
        )

    def get_processed_crash(self, crash_id):
        """Get the processed crash.

        :returns: dict

        :raises CrashIDNotFound: if file does not exist

        """
        path = build_keys("processed_crash", crash_id)[0]
        try:
            processed_crash_as_string = self.load_file(path)
            return json.loads(processed_crash_as_string)
        except self.connection.KeyNotFound as exc:
            raise CrashIDNotFound(f"{crash_id} not found: {exc}") from exc


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
        self.save_file(path, data)

    def get_processed_crash(self, crash_id):
        """Get a crash report from the S3 bucket.

        :returns: dict

        :raises CrashIDNotFound: if file does not exist

        """
        path = build_keys("crash_report", crash_id)[0]
        try:
            crash_report_as_str = self.load_file(path)
            return json.loads(crash_report_as_str)
        except self.connection.KeyNotFound as exc:
            raise CrashIDNotFound(f"{crash_id} not found: {exc}") from exc
