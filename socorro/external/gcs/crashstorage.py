# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import os

from google.auth.credentials import AnonymousCredentials
from google.api_core.exceptions import NotFound
from google.cloud import storage
from more_itertools import chunked

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    CrashIDNotFound,
    MemoryDumpsMapping,
    get_datestamp,
    dict_to_str,
    list_to_str,
    str_to_list,
)
from socorro.lib import external_common, MissingArgumentError, BadArgumentError, libooid
from socorro.lib.libjsonschema import JsonSchemaReducer
from socorro.lib.libsocorrodataschema import (
    get_schema,
    permissions_transform_function,
    SocorroDataReducer,
    transform_schema,
)
from socorro.schemas import TELEMETRY_SOCORRO_CRASH_SCHEMA


def build_keys(name_of_thing, crashid):
    """Builds a list of pseudo-filenames

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


class GcsCrashStorage(CrashStorageBase):
    """Saves and loads crash data to GCS"""

    def __init__(
        self,
        bucket="crashstats",
        dump_file_suffix=".dump",
        metrics_prefix="processor.gcs",
    ):
        """
        :arg bucket: the GCS bucket to save to
        :arg dump_file_suffix: the suffix used to identify a dump file (for use in temp
            files)
        :arg metrics_prefix: the metrics prefix for markus

        """
        super().__init__()

        if emulator := os.environ.get("STORAGE_EMULATOR_HOST"):
            self.logger.debug(
                "STORAGE_EMULATOR_HOST detected, connecting to emulator: %s",
                emulator,
            )
            self.client = storage.Client(
                credentials=AnonymousCredentials(),
                project=os.environ.get("STORAGE_PROJECT_ID"),
            )
        else:
            self.client = storage.Client()

        self.bucket = bucket
        self.dump_file_suffix = dump_file_suffix

    def load_file(self, path):
        bucket = self.client.bucket(self.bucket)
        blob = bucket.blob(path)
        return blob.download_as_bytes()

    def save_file(self, path, data):
        bucket = self.client.bucket(self.bucket)
        blob = bucket.blob(path)
        blob.upload_from_string(data)

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        """Save raw crash data to GCS bucket.

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

    def list_objects_paginator(self, prefix, page_size=1000):
        """Yield pages of object keys in the bucket that have a specified key prefix

        :arg prefix: the prefix to look at
        :arg page_size: the number of results to return per page

        :returns: generator of pages (lists) of object keys

        """
        for page in chunked(
            self.client.list_blobs(
                bucket_or_name=self.bucket, prefix=prefix, page_size=page_size
            ),
            page_size,
        ):
            yield [blob.name for blob in page]

    def exists_object(self, key):
        """Returns whether the object exists in the bucket

        :arg key: the key to check

        :returns: bool

        """
        bucket = self.client.bucket(self.bucket)
        return bucket.blob(key).exists()

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
            except NotFound:
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
        except NotFound as exc:
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
        except NotFound as exc:
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
        except NotFound as exc:
            raise CrashIDNotFound(f"{crash_id} not found: {exc}") from exc
        return json.loads(processed_crash_as_string)

    def get(self, **kwargs):
        """Return JSON data of a crash report, given its uuid."""
        # FIXME(relud): This method is used by the webapp API middleware nonsense. It
        # shouldn't exist here. We should move it to the webapp.
        filters = [
            ("uuid", None, str),
            ("datatype", None, str),
            ("name", None, str),  # only applicable if datatype == 'raw'
        ]
        params = external_common.parse_arguments(filters, kwargs, modern=True)

        if not params["uuid"]:
            raise MissingArgumentError("uuid")

        if not libooid.is_crash_id_valid(params["uuid"]):
            raise BadArgumentError("uuid")

        if not params["datatype"]:
            raise MissingArgumentError("datatype")

        datatype_method_mapping = {
            # Minidumps
            "raw": "get_raw_dump",
            # Raw Crash
            "meta": "get_raw_crash",
            # Redacted processed crash
            "processed": "get_processed_crash",
        }
        if params["datatype"] not in datatype_method_mapping:
            raise BadArgumentError(params["datatype"])
        get = self.__getattribute__(datatype_method_mapping[params["datatype"]])
        try:
            if params["datatype"] == "raw":
                return get(params["uuid"], name=params["name"])
            else:
                return get(params["uuid"])
        except CrashIDNotFound as cidnf:
            self.logger.warning("%s not found: %s", params["datatype"], cidnf)
            # The CrashIDNotFound exception that happens inside the
            # crashstorage is too revealing as exception message
            # contains information about buckets and prefix keys.
            # Re-wrap it here so the message is just the crash ID.
            raise CrashIDNotFound(params["uuid"]) from cidnf


class TelemetryGcsCrashStorage(GcsCrashStorage):
    """Sends a subset of the processed crash to a GCS bucket

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
        """Get a crash report from the GCS bucket.

        :returns: dict

        :raises CrashIDNotFound: if file does not exist

        """
        path = build_keys("crash_report", crash_id)[0]
        try:
            crash_report_as_str = self.load_file(path)
        except NotFound as exc:
            raise CrashIDNotFound(f"{crash_id} not found: {exc}") from exc
        return json.loads(crash_report_as_str)

    def get(self, **kwargs):
        """Return JSON data of a crash report, given its uuid."""
        # FIXME(relud): This method is used by the webapp API middleware nonsense. It
        # shouldn't exist here. We should move it to the webapp.
        filters = [("uuid", None, str)]
        params = external_common.parse_arguments(filters, kwargs, modern=True)

        if not params["uuid"]:
            raise MissingArgumentError("uuid")

        try:
            return self.get_processed_crash(params["uuid"])
        except CrashIDNotFound as cidnf:
            self.logger.warning("telemetry crash not found: %s", cidnf)
            # The CrashIDNotFound exception that happens inside the
            # crashstorage is too revealing as exception message contains
            # information about buckets and prefix keys. Re-wrap it here so the
            # message is just the crash ID.
            raise CrashIDNotFound(params["uuid"]) from cidnf
