# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/

import boto
import boto.s3.connection
import boto.exception
import json
import os
import socket
import datetime
import contextlib

from socorro.external.crashstorage_base import (
    CrashStorageBase,
    CrashIDNotFound
)
from socorro.lib.util import DotDict

from configman import Namespace
from configman.converters import class_converter, py_obj_to_str


#==============================================================================
class BotoS3CrashStorage(CrashStorageBase):
    """This class sends processed crash reports to an end point reachable
    by the boto S3 library.
    """

    required_config = Namespace()
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
        'host',
        doc="The hostname (leave empty for AWS)",
        default="",
        reference_value_from='resource.boto',
    )
    required_config.add_option(
        'port',
        doc="The network port (leave at 0 for AWS)",
        default=0,
        reference_value_from='resource.boto',
    )
    required_config.add_option(
        'access_key',
        doc="access key",
        default="",
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
        'secret_access_key',
        doc="secret access key",
        default="",
        secret=True,
        reference_value_from='secrets.boto',
    )
    required_config.add_option(
        'bucket_name',
        doc="The name of the bucket.",
        default='crashstats',
        reference_value_from='resource.boto',
        likely_to_be_changed=True,
    )
    required_config.add_option(
        'prefix',
        doc="a prefix to use inside the bucket",
        default='dev',
        reference_value_from='resource.boto',
        likely_to_be_changed=True,
    )
    required_config.add_option(
        'calling_format',
        doc="fully qualified python path to the boto calling format function",
        default='boto.s3.connection.SubdomainCallingFormat',
        from_string_converter=class_converter,
        reference_value_from='resource.boto',
        likely_to_be_changed=True,
    )

    operational_exceptions = (
        socket.timeout,
        # wild guesses at retriable exceptions
        boto.exception.PleaseRetryException,
        boto.exception.ResumableTransferDisposition,
        boto.exception.ResumableUploadException,
    )

    conditional_exceptions = (
        boto.exception.StorageResponseError
    )

    #--------------------------------------------------------------------------
    def is_operational_exception(self, x):
        if "not found, no value returned" in str(x):
            # the not found error needs to be re-tryable to compensate for
            # eventual consistency.  However, a method capable of raising this
            # exception should never be used with a transaction executor that
            # has infinite back off.
            return True
        #elif   # for further cases...
        return False

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(BotoS3CrashStorage, self).__init__(
            config,
            quit_check_callback
        )

        self._bucket_name = config.bucket_name

        self.transaction = config.transaction_executor_class(
            config,
            self,  # we are our own connection
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
            self,  # we are our own connection
            quit_check_callback
        )


        # short cuts to external resources - makes testing/mocking easier
        self._connect_to_endpoint = boto.connect_s3
        self._calling_format = config.calling_format
        self._CreateError = boto.exception.S3CreateError
        self._S3ResponseError = boto.exception.S3ResponseError
        self._open = open

    #--------------------------------------------------------------------------
    @staticmethod
    def build_s3_dirs(prefix, name_of_thing, crash_id):
        """
        Use S3 pseudo-directories to make it easier to list/expire later
        {{prefix}}/{{version}}/{{name_of_thing}}/{{crash_id}}
        """
        version = 'v1'
        return '%s/%s/%s/%s' % (prefix, version, name_of_thing, crash_id)

    #--------------------------------------------------------------------------
    @staticmethod
    def do_save_raw_crash(boto_s3_store, raw_crash, dumps, crash_id):
        raw_crash_as_string = boto_s3_store._convert_mapping_to_string(
            raw_crash
        )
        boto_s3_store._submit_to_boto_s3(
            crash_id,
            "raw_crash",
            raw_crash_as_string
        )
        dump_names_as_string = boto_s3_store._convert_list_to_string(
            dumps.keys()
        )
        boto_s3_store._submit_to_boto_s3(
            crash_id,
            "dump_names",
            dump_names_as_string
        )
        for dump_name, dump in dumps.iteritems():
            if dump_name in (None, '', 'upload_file_minidump'):
                dump_name = 'dump'
            boto_s3_store._submit_to_boto_s3(crash_id, dump_name, dump)

    #--------------------------------------------------------------------------
    def save_raw_crash(self, raw_crash, dumps, crash_id):
        self.transaction(self.do_save_raw_crash, raw_crash, dumps, crash_id)

    #--------------------------------------------------------------------------
    @staticmethod
    def _do_save_processed(boto_s3_store, processed_crash):
        crash_id = processed_crash['uuid']
        processed_crash_as_string = boto_s3_store._convert_mapping_to_string(
            processed_crash
        )
        boto_s3_store._submit_to_boto_s3(
            crash_id,
            "processed_crash",
            processed_crash_as_string
        )

    #--------------------------------------------------------------------------
    def save_processed(self, processed_crash):
        self.transaction(self._do_save_processed, processed_crash)

    #--------------------------------------------------------------------------
    def save_raw_and_processed(self, raw_crash, dumps, processed_crash, crash_id):
        """ bug 866973 - do not put raw_crash back into permanent storage again
            We are doing this in lieu of a queuing solution that could allow
            us to operate an independent crashmover. When the queuing system
            is implemented, we could remove this, and have the raw crash
            saved by a crashmover that's consuming crash_ids the same way
            that the processor consumes them.

            See further comments in the ProcesorApp class.
        """
        self.save_processed(processed_crash)

    #--------------------------------------------------------------------------
    @staticmethod
    def do_get_raw_crash(boto_s3_store, crash_id):
        try:
            raw_crash_as_string = boto_s3_store._fetch_from_boto_s3(
                crash_id,
                "raw_crash"
            )
            return json.loads(raw_crash_as_string, object_hook=DotDict)
        except boto.exception.StorageResponseError, x:
            raise CrashIDNotFound(
                '%s not found: %s' % (crash_id, x)
            )

    #--------------------------------------------------------------------------
    def get_raw_crash(self, crash_id):
        return self.transaction_for_get(self.do_get_raw_crash, crash_id)

    #--------------------------------------------------------------------------
    @staticmethod
    def do_get_raw_dump(boto_s3_store, crash_id, name=None):
        try:
            if name in (None, '', 'upload_file_minidump'):
                name = 'dump'
            a_dump = boto_s3_store._fetch_from_boto_s3(crash_id, name)
            return a_dump
        except boto.exception.StorageResponseError, x:
            raise CrashIDNotFound(
                '%s not found: %s' % (crash_id, x)
            )

    #--------------------------------------------------------------------------
    def get_raw_dump(self, crash_id, name=None):
        return self.transaction_for_get(self.do_get_raw_dump, crash_id, name)

    #--------------------------------------------------------------------------
    @staticmethod
    def do_get_raw_dumps(boto_s3_store, crash_id):
        try:
            dump_names_as_string = boto_s3_store._fetch_from_boto_s3(
                crash_id,
                "dump_names"
            )
            dump_names = boto_s3_store._convert_string_to_list(
                dump_names_as_string
            )
            dumps = {}
            for dump_name in dump_names:
                if dump_name in (None, '', 'upload_file_minidump'):
                    dump_name = 'dump'
                dumps[dump_name] = boto_s3_store._fetch_from_boto_s3(
                    crash_id,
                    dump_name
                )
            return dumps
        except boto.exception.StorageResponseError, x:
            raise CrashIDNotFound(
                '%s not found: %s' % (crash_id, x)
            )

    #--------------------------------------------------------------------------
    def get_raw_dumps(self, crash_id):
        return self.transaction_for_get(self.do_get_raw_dumps, crash_id)

    #--------------------------------------------------------------------------
    @staticmethod
    def do_get_raw_dumps_as_files(boto_s3_store, crash_id):
        """the default implementation of fetching all the dumps as files on
        a file system somewhere.  returns a list of pathnames.

        parameters:
           crash_id - the id of a dump to fetch"""
        try:
            dumps_mapping = boto_s3_store.get_raw_dumps(crash_id)
            name_to_pathname_mapping = {}
            for a_dump_name, a_dump in dumps_mapping.iteritems():
                if a_dump_name in (None, '', 'dump'):
                    a_dump_name = 'upload_file_minidump'
                dump_pathname = os.path.join(
                    boto_s3_store.config.temporary_file_system_storage_path,
                    "%s.%s.TEMPORARY%s" % (
                        crash_id,
                        a_dump_name,
                        boto_s3_store.config.dump_file_suffix
                    )
                )
                name_to_pathname_mapping[a_dump_name] = dump_pathname
                with boto_s3_store._open(dump_pathname, 'wb') as f:
                    f.write(a_dump)
            return name_to_pathname_mapping
        except boto.exception.StorageResponseError, x:
            raise CrashIDNotFound(
                '%s not found: %s' % (crash_id, x)
            )

    #--------------------------------------------------------------------------
    def get_raw_dumps_as_files(self, crash_id):
        return self.transaction_for_get(self.do_get_raw_dumps_as_files, crash_id)

    #--------------------------------------------------------------------------
    @staticmethod
    def _do_get_unredacted_processed(boto_s3_store, crash_id):
        try:
            processed_crash_as_string = boto_s3_store._fetch_from_boto_s3(
                crash_id,
                "processed_crash"
            )
            return json.loads(
                processed_crash_as_string,
                object_hook=DotDict
            )
        except boto.exception.StorageResponseError, x:
            raise CrashIDNotFound(
                '%s not found: %s' % (crash_id, x)
            )

    #--------------------------------------------------------------------------
    def get_unredacted_processed(self, crash_id):
        return self.transaction_for_get(self._do_get_unredacted_processed, crash_id)

    #--------------------------------------------------------------------------
    def _get_bucket(self, conn, bucket_name):
        try:
            return self._bucket_cache
        except AttributeError:
            self._bucket_cache = conn.get_bucket(bucket_name)
            return self._bucket_cache

    #--------------------------------------------------------------------------
    def _get_or_create_bucket(self, conn, bucket_name):
        try:
            return self._bucket_cache
        except AttributeError:
            try:
                self._bucket_cache = conn.get_bucket(bucket_name)
            except self._S3ResponseError:
                self._bucket_cache = conn.create_bucket(bucket_name)
            return self._bucket_cache

    #--------------------------------------------------------------------------
    def _submit_to_boto_s3(self, crash_id, name_of_thing, thing):
        """submit something to boto.
        """
        if not isinstance(thing, basestring):
            raise Exception('can only submit strings to boto')

        conn = self._connect()
        bucket = self._get_or_create_bucket(conn, self.config.bucket_name)

        key = self.build_s3_dirs(self.config.prefix, name_of_thing, crash_id)

        storage_key = bucket.new_key(key)
        storage_key.set_contents_from_string(thing)

    #--------------------------------------------------------------------------
    def _fetch_from_boto_s3(self, crash_id, name_of_thing):
        """retrieve something from boto.
        """
        conn = self._connect()
        bucket = self._get_bucket(conn, self.config.bucket_name)

        key = self.build_s3_dirs(self.config.prefix, name_of_thing, crash_id)

        storage_key = bucket.get_key(key)
        if storage_key is None:
            raise CrashIDNotFound('%s not found, no value returned' % crash_id)
        return storage_key.get_contents_as_string()

    #--------------------------------------------------------------------------
    def _connect(self):
        try:
            return self.connection
        except AttributeError:
            kwargs = {
                "aws_access_key_id": self.config.access_key,
                "aws_secret_access_key": self.config.secret_access_key,
                "is_secure": True,
                "calling_format": self._calling_format(),
            }
            if self.config.host:
                kwargs["host"] = self.config.host
            if self.config.port:
                kwargs["port"] = self.config.port
            self.connection = self._connect_to_endpoint(**kwargs)
            return self.connection

    #--------------------------------------------------------------------------
    def _convert_mapping_to_string(self, a_mapping):
        self._stringify_dates_in_dict(a_mapping)
        return json.dumps(a_mapping)

    #--------------------------------------------------------------------------
    def _convert_list_to_string(self, a_list):
        return json.dumps(a_list)

    #--------------------------------------------------------------------------
    def _convert_string_to_list(self, a_string):
        return json.loads(a_string)

    #--------------------------------------------------------------------------
    @staticmethod
    def _stringify_dates_in_dict(items):
        for k, v in items.iteritems():
            if isinstance(v, datetime.datetime):
                items[k] = v.strftime("%Y-%m-%d %H:%M:%S.%f")
        return items

    # because this crashstorage class operates as its own connection class
    # these function must be present.  The transaction executor will use them
    # to coordinate retries
    # essentially to function as a connection, this class must fullfill the
    # API contract with connection objects recognized by the transaction
    # manager. The following functions are required by that API.
    #--------------------------------------------------------------------------
    def commit(self):
        """boto doesn't support transactions so this silently
        does nothing"""

    #--------------------------------------------------------------------------
    def rollback(self):
        """boto doesn't support transactions so this silently
        does nothing"""

    #--------------------------------------------------------------------------
    @contextlib.contextmanager
    def __call__(self):
        """this class will serve as its own context manager.  That enables it
        to use the transaction_executor class for retries"""
        yield self

    #--------------------------------------------------------------------------
    def in_transaction(self, dummy):
        """boto doesn't support transactions, so it is never in
        a transaction."""
        return False

    #--------------------------------------------------------------------------
    def force_reconnect(self):
        try:
            del self.connection
        except AttributeError:
            # already deleted, ignorable
            pass


#==============================================================================
class SupportReasonAPIStorage(BotoS3CrashStorage):
    """Used to send a small subset of processed crash data the Support Reason
       API back-end. This is effectively a highly lossy S3 storage mechanism.
       bug 1066058
    """

    # intially we wanted the support reason class to use a different bucket,
    # but the following override interferes with the base class.  I suspect
    # we'll end up using a prefix instead of differing bucket name in the
    # future.  Leaving this code in place for the moment
    #BotoS3CrashStorage.required_config.bucket_name.set_default(
        #val='mozilla-support-reason',
        #force=True
    #)

    #--------------------------------------------------------------------------
    @staticmethod
    def _do_save_processed(boto_s3_store, processed_crash):
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
        boto_s3_store._submit_to_boto_s3(
            crash_id,
            'support_reason',
            json.dumps(content)
        )

    #--------------------------------------------------------------------------
    def save_raw_crash(self, raw_crash, dumps, crash_id):
        """There are no scenarios in which the raw crash could possibly be of
        interest to the Support Reason API, therefore this function does
        nothing; however it is necessary for compatibility purposes.
        """
        pass


