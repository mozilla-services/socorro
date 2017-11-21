# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/

import json
import time

import json_schema_reducer
from socorro.lib.converters import change_default

from configman import Namespace
from configman.converters import class_converter, py_obj_to_str

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    CrashIDNotFound,
    MemoryDumpsMapping,
)
from socorro.external.boto.connection_context import (
    SimpleDatePrefixKeyBuilder
)
from socorro.external.es.super_search_fields import SuperSearchFields
from socorro.schemas import CRASH_REPORT_JSON_SCHEMA


class BotoCrashStorage(CrashStorageBase):
    """This class sends processed crash reports to an end point reachable
    by the boto S3 library.
    """
    required_config = Namespace()
    required_config.add_option(
        "resource_class",
        default=(
            'socorro.external.boto.connection_context.ConnectionContextBase'
        ),
        doc=(
            'fully qualified dotted Python classname to handle Boto '
            'connections'
        ),
        from_string_converter=class_converter,
        reference_value_from='resource.boto'
    )
    required_config.add_option(
        'transaction_executor_class_for_get',
        default="socorro.database.transaction_executor."
        "TransactionExecutorWithLimitedBackoff",
        doc='a class that will manage transactions',
        from_string_converter=class_converter,
        reference_value_from='resource.boto',
    )
    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
        "TransactionExecutorWithLimitedBackoff",
        doc='a class that will manage transactions',
        from_string_converter=class_converter,
        reference_value_from='resource.boto',
    )
    required_config.add_option(
        'temporary_file_system_storage_path',
        doc='a local filesystem path where dumps temporarily '
            'during processing',
        default='/home/socorro/temp',
        reference_value_from='resource.boto',
    )
    required_config.add_option(
        'dump_file_suffix',
        doc='the suffix used to identify a dump file (for use in temp files)',
        default='.dump',
        reference_value_from='resource.boto',
    )
    required_config.add_option(
        'json_object_hook',
        default='socorro.lib.util.DotDict',
        from_string_converter=class_converter,
    )

    def is_operational_exception(self, x):
        if "not found, no value returned" in str(x):
            # the not found error needs to be re-tryable to compensate for
            # eventual consistency.  However, a method capable of raising this
            # exception should never be used with a transaction executor that
            # has infinite back off.
            return True
        #elif   # for further cases...
        return False

    def __init__(self, config, quit_check_callback=None):
        super(BotoCrashStorage, self).__init__(
            config,
            quit_check_callback
        )

        self.connection_source = config.resource_class(config)
        self.transaction = config.transaction_executor_class(
            config,
            self.connection_source,
            quit_check_callback
        )
        if config.transaction_executor_class_for_get.is_infinite:
            self.config.logger.error(
                'the class %s identifies itself as an infinite iterator. '
                'As a TransactionExecutor for reads from Boto, this may '
                'result in infinite loops that will consume threads forever.'
                % py_obj_to_str(config.transaction_executor_class_for_get)
            )

        self.transaction_for_get = config.transaction_executor_class_for_get(
            config,
            self.connection_source,
            quit_check_callback
        )

    @staticmethod
    def do_save_raw_crash(boto_connection, raw_crash, dumps, crash_id):
        if dumps is None:
            dumps = MemoryDumpsMapping()
        raw_crash_as_string = boto_connection._convert_mapping_to_string(
            raw_crash
        )
        boto_connection.submit(
            crash_id,
            "raw_crash",
            raw_crash_as_string
        )
        dump_names_as_string = boto_connection._convert_list_to_string(
            dumps.keys()
        )
        boto_connection.submit(
            crash_id,
            "dump_names",
            dump_names_as_string
        )

        # we don't know what type of dumps mapping we have.  We do know,
        # however, that by calling the memory_dump_mapping method, we will
        # get a MemoryDumpMapping which is exactly what we need.
        dumps = dumps.as_memory_dumps_mapping()
        for dump_name, dump in dumps.iteritems():
            if dump_name in (None, '', 'upload_file_minidump'):
                dump_name = 'dump'
            boto_connection.submit(crash_id, dump_name, dump)

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        self.transaction(self.do_save_raw_crash, raw_crash, dumps, crash_id)

    @staticmethod
    def _do_save_processed(boto_connection, processed_crash):
        crash_id = processed_crash['uuid']
        processed_crash_as_string = boto_connection._convert_mapping_to_string(
            processed_crash
        )
        boto_connection.submit(
            crash_id,
            "processed_crash",
            processed_crash_as_string
        )

    def save_processed(self, processed_crash):
        self.transaction(self._do_save_processed, processed_crash)

    def save_raw_and_processed(
        self,
        raw_crash,
        dumps,
        processed_crash,
        crash_id
    ):
        """ bug 866973 - do not put raw_crash back into permanent storage again
            We are doing this in lieu of a queuing solution that could allow
            us to operate an independent crashmover. When the queuing system
            is implemented, we could remove this, and have the raw crash
            saved by a crashmover that's consuming crash_ids the same way
            that the processor consumes them.

            See further comments in the ProcesorApp class.
        """
        self.save_processed(processed_crash)

    @staticmethod
    def do_get_raw_crash(boto_connection, crash_id, json_object_hook):
        try:
            raw_crash_as_string = boto_connection.fetch(
                crash_id,
                "raw_crash"
            )
            return json.loads(
                raw_crash_as_string,
                object_hook=json_object_hook
            )
        except boto_connection.ResponseError as x:
            raise CrashIDNotFound(
                '%s not found: %s' % (crash_id, x)
            )

    def get_raw_crash(self, crash_id):
        return self.transaction_for_get(
            self.do_get_raw_crash,
            crash_id,
            self.config.json_object_hook
        )

    @staticmethod
    def do_get_raw_dump(boto_connection, crash_id, name=None):
        try:
            if name in (None, '', 'upload_file_minidump'):
                name = 'dump'
            a_dump = boto_connection.fetch(crash_id, name)
            return a_dump
        except boto_connection.ResponseError as x:
            raise CrashIDNotFound(
                '%s not found: %s' % (crash_id, x)
            )

    def get_raw_dump(self, crash_id, name=None):
        return self.transaction_for_get(self.do_get_raw_dump, crash_id, name)

    @staticmethod
    def do_get_raw_dumps(boto_connection, crash_id):
        try:
            dump_names_as_string = boto_connection.fetch(
                crash_id,
                "dump_names"
            )
            dump_names = boto_connection._convert_string_to_list(
                dump_names_as_string
            )
            # when we fetch the dumps, they are by default in memory, so we'll
            # put them into a MemoryDumpMapping.
            dumps = MemoryDumpsMapping()
            for dump_name in dump_names:
                if dump_name in (None, '', 'upload_file_minidump'):
                    dump_name = 'dump'
                dumps[dump_name] = boto_connection.fetch(
                    crash_id,
                    dump_name
                )
            return dumps
        except boto_connection.ResponseError as x:
            raise CrashIDNotFound(
                '%s not found: %s' % (crash_id, x)
            )

    def get_raw_dumps(self, crash_id):
        """this returns a MemoryDumpsMapping"""
        return self.transaction_for_get(self.do_get_raw_dumps, crash_id)

    def get_raw_dumps_as_files(self, crash_id):
        in_memory_dumps = self.get_raw_dumps(crash_id)
        # convert our native memory dump mapping into a file dump mapping.
        return in_memory_dumps.as_file_dumps_mapping(
            crash_id,
            self.config.temporary_file_system_storage_path,
            self.config.dump_file_suffix
        )

    @staticmethod
    def _do_get_unredacted_processed(
        boto_connection,
        crash_id,
        json_object_hook,
    ):
        try:
            processed_crash_as_string = boto_connection.fetch(
                crash_id,
                "processed_crash"
            )
            return json.loads(
                processed_crash_as_string,
                object_hook=json_object_hook,
            )
        except boto_connection.ResponseError as x:
            raise CrashIDNotFound(
                '%s not found: %s' % (crash_id, x)
            )

    def get_unredacted_processed(self, crash_id):
        return self.transaction_for_get(
            self._do_get_unredacted_processed,
            crash_id,
            self.config.json_object_hook,
        )


class BotoS3CrashStorage(BotoCrashStorage):
    required_config = Namespace()
    required_config.resource_class = change_default(
        BotoCrashStorage,
        'resource_class',
        'socorro.external.boto.connection_context.RegionalS3ConnectionContext'
    )


class TelemetryBotoS3CrashStorage(BotoS3CrashStorage):
    """Sends a subset of the processed crash to an S3 bucket

    The subset of the processed crash is based on the JSON Schema which is
    derived from "socorro/external/es/super_search_fields.py".

    This uses a boto connection context with one twist: if you set
    "resource.boto.telemetry_bucket_name", then that will override the value.

    """

    required_config = Namespace()
    required_config.resource_class = change_default(
        BotoCrashStorage,
        'resource_class',
        'socorro.external.boto.connection_context.RegionalS3ConnectionContext'
    )
    required_config.add_option(
        'telemetry_bucket_name',
        default='',
        reference_value_from='resource.boto',
        doc='if set, overrides resource_class bucket name'
    )

    required_config.elasticsearch = Namespace()
    required_config.elasticsearch.add_option(
        'elasticsearch_class',
        default='socorro.external.es.connection_context.ConnectionContext',
        from_string_converter=class_converter,
        reference_value_from='resource.elasticsearch',
    )

    def __init__(self, config, *args, **kwargs):
        # This class requires that we use
        # SimpleDatePrefixKeyBuilder, so we stomp on the configuration
        # to make absolutely sure it gets set that way.
        config.keybuilder_class = SimpleDatePrefixKeyBuilder
        super(TelemetryBotoS3CrashStorage, self).__init__(
            config, *args, **kwargs
        )

        if config.telemetry_bucket_name:
            # If we have a telemetry.bucket_name set, then stomp on it with
            # config.telemetry_bucket_name.

            # FIXME(willkg): It'd be better if we could detect whether the
            # connection context bucket_name was set at all (it's a default
            # value, or the value of resource.boto.bucket_name).
            config.logger.info(
                'Using %s for TelemetryBotoS3CrashStorage bucket', config.telemetry_bucket_name
            )
            self.connection_source.config.bucket_name = config.telemetry_bucket_name

    def _get_all_fields(self):
        if (
            hasattr(self, '_all_fields') and
            hasattr(self, '_all_fields_timestamp')
        ):
            # we might have it cached
            age = time.time() - self._all_fields_timestamp
            if age < 60 * 60:
                # fresh enough
                return self._all_fields

        self._all_fields = SuperSearchFields(config=self.config).get()
        self._all_fields_timestamp = time.time()
        return self._all_fields

    def save_raw_and_processed(
        self,
        raw_crash,
        dumps,
        processed_crash,
        crash_id
    ):
        all_fields = self._get_all_fields()
        crash_report = {}

        # TODO Opportunity of optimization;
        # We could inspect CRASH_REPORT_JSON_SCHEMA and get a list
        # of all (recursive) keys that are in there and use that
        # to limit the two following loops to not bother
        # filling up `crash_report` with keys that will never be
        # needed.

        # Rename fields in raw_crash.
        raw_fields_map = dict(
            (x['in_database_name'], x['name'])
            for x in all_fields.values()
            if x['namespace'] == 'raw_crash'
        )
        for key, val in raw_crash.items():
            crash_report[raw_fields_map.get(key, key)] = val

        # Rename fields in processed_crash.
        processed_fields_map = dict(
            (x['in_database_name'], x['name'])
            for x in all_fields.values()
            if x['namespace'] == 'processed_crash'
        )
        for key, val in processed_crash.items():
            crash_report[processed_fields_map.get(key, key)] = val

        # Validate crash_report.
        crash_report = json_schema_reducer.make_reduced_dict(
            CRASH_REPORT_JSON_SCHEMA, crash_report
        )
        self.save_processed(crash_report)

    @staticmethod
    def _do_save_processed(boto_connection, processed_crash):
        """Overriding this method so we can control the "name of thing"
        prefix used to upload to S3."""
        crash_id = processed_crash['uuid']
        processed_crash_as_string = boto_connection._convert_mapping_to_string(
            processed_crash
        )
        boto_connection.submit(
            crash_id,
            "crash_report",
            processed_crash_as_string
        )


class SupportReasonAPIStorage(BotoS3CrashStorage):
    """Used to send a small subset of processed crash data the Support Reason
       API back-end. This is effectively a highly lossy S3 storage mechanism.
       bug 1066058
    """

    # intially we wanted the support reason class to use a different bucket
    # I suspect that we'll end up using a prefix instead of differing bucket
    # name in the future.  Leaving this code in place for the moment

    @staticmethod
    def _do_save_processed(boto_connection, processed_crash):
        """Replaces the function of the same name in the parent class.
        """
        crash_id = processed_crash['uuid']

        try:
            # Set up the data chunk to be passed to S3.
            reason = \
                processed_crash['classifications']['support']['classification']
            content = {
                'crash_id': crash_id,
                'reasons': [reason]
            }
        except KeyError:
            # No classifier was found for this crash.
            return

        # Submit the data chunk to S3.
        boto_connection.submit(
            crash_id,
            'support_reason',
            json.dumps(content)
        )

    def save_raw_crash(self, raw_crash, dumps, crash_id):
        """There are no scenarios in which the raw crash could possibly be of
        interest to the Support Reason API, therefore this function does
        nothing; however it is necessary for compatibility purposes.
        """
        pass
