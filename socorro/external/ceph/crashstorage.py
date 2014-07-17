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
from configman.converters import class_converter


#==============================================================================
class BotoS3CrashStorage(CrashStorageBase):
    """This class sends processed crash reports to an end point reachable
    by the boto S3 library.
    """

    required_config = Namespace()
    required_config.add_option(
        'transaction_executor_class',
        default="socorro.database.transaction_executor."
        "TransactionExecutorWithLimitedBackoff",
        doc='a class that will manage transactions',
        from_string_converter=class_converter,
        reference_value_from='resource.ceph',
    )
    required_config.add_option(
        'host',
        doc="The hostname of the S3 crash storage to submit to",
        default="ceph.dev.phx1.mozilla.com",
        reference_value_from='resource.ceph',
    )
    required_config.add_option(
        'port',
        doc="The network port of the S3 crash storage to submit to",
        default=80,
        reference_value_from='resource.ceph',
    )
    required_config.add_option(
        'access_key',
        doc="access key",
        default="",
        reference_value_from='resource.ceph',
    )
    required_config.add_option(
        'secret_access_key',
        doc="secret access key",
        default="",
        reference_value_from='secrets.ceph',
    )
    #required_config.add_option(
        #'buckets',
        #doc="How to organize the buckets (default: daily)",
        #default="daily",
        #reference_value_from='resource.ceph',
    #)

    operational_exceptions = (
        socket.timeout,
        # wild guesses at retriable exceptions
        boto.exception.PleaseRetryException,
        boto.exception.ResumableTransferDisposition,
        boto.exception.ResumableUploadException,
    )

    conditional_exceptions = ()

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(BotoS3CrashStorage, self).__init__(
            config,
            quit_check_callback
        )
        self._bucket_cache = {}
        self.transaction = config.transaction_executor_class(
            config,
            self,  # we are our own connection
            quit_check_callback
        )

        # short cuts to external resources - makes testing/mocking easier
        self._connect_to_endpoint = boto.connect_s3
        self._calling_format = boto.s3.connection.OrdinaryCallingFormat
        self._CreateError = boto.exception.S3CreateError
        self._open = open

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
    def _do_save_processed(self, processed_crash):
        crash_id = processed_crash['uuid']
        processed_crash_as_string = self._convert_mapping_to_string(
            processed_crash
        )
        self._submit_to_boto_s3(
            crash_id,
            "processed_crash",
            processed_crash_as_string
        )

    #--------------------------------------------------------------------------
    def save_processed(self, processed_crash):
        self.transaction(self._do_save_processed, processed_crash)

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
        return self.transaction(self.do_get_raw_crash, crash_id)

    #--------------------------------------------------------------------------
    @staticmethod
    def do_get_raw_dump(boto_s3_store, crash_id, name=None):
        try:
            if name is None:
                name = 'dump'
            a_dump = boto_s3_store._fetch_from_boto_s3(crash_id, name)
            return a_dump
        except boto.exception.StorageResponseError, x:
            raise CrashIDNotFound(
                '%s not found: %s' % (crash_id, x)
            )

    #--------------------------------------------------------------------------
    def get_raw_dump(self, crash_id, name=None):
        return self.transaction(self.do_get_raw_dump, crash_id, name)

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
        return self.transaction(self.do_get_raw_dumps, crash_id)

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
        return self.transaction(self.do_get_raw_dumps_as_files, crash_id)

    #--------------------------------------------------------------------------
    @staticmethod
    def do_get_unredacted_processed(boto_s3_store, crash_id):
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
        return self.transaction(self.do_get_unredacted_processed, crash_id)

    #--------------------------------------------------------------------------
    @staticmethod
    def _create_bucket_name_for_crash_id(crash_id):
        """feel free to subclass and override this implementation for something
        more creative"""
        return crash_id[-6:]

    #--------------------------------------------------------------------------
    def _get_bucket(self, conn, bucket_name):
        try:
            return self._bucket_cache[bucket_name]
        except KeyError:
            now = datetime.datetime.now()
            self._bucket_cache[bucket_name] = conn.create_bucket(bucket_name)
            delta = datetime.datetime.now() - now
            self.config.logger.debug(
                'conn.create_bucket %s: %s', bucket_name, delta
            )
            return self._bucket_cache[bucket_name]

    #--------------------------------------------------------------------------
    def _submit_to_boto_s3(self, crash_id, name_of_thing, thing):
        """submit something to ceph.
        """
        if not isinstance(thing, basestring):
            raise Exception('can only submit strings to Ceph')

        conn = self._connect()

        # create/connect to bucket
        try:
            # return a bucket for a given day
            the_day_bucket_name = self._create_bucket_name_for_crash_id(
                crash_id
            )
            bucket = self._get_bucket(conn, the_day_bucket_name)
        except self._CreateError:
            # TODO: oops, bucket already taken
            # shouldn't ever happen, but let's handle this
            self.config.logger.error(
                'Ceph bucket creation/connection has failed for %s'
                % the_day_bucket_name,
                exc_info=True
            )
            raise

        key = "%s.%s" % (crash_id, name_of_thing)

        storage_key = bucket.new_key(key)
        storage_key.set_contents_from_string(thing)

    #--------------------------------------------------------------------------
    def _fetch_from_boto_s3(self, crash_id, name_of_thing):
        """submit something to ceph.
        """
        conn = self._connect()

        # create/connect to bucket
        try:
            # return a bucket for a given day
            the_day_bucket_name = self._create_bucket_name_for_crash_id(
                crash_id
            )
            bucket = self._get_bucket(conn, the_day_bucket_name)
        except self._CreateError:
            # TODO: oops, bucket already taken
            # shouldn't ever happen, but let's handle this
            self.config.logger.error(
                'Ceph bucket creation/connection has failed for %s'
                % the_day_bucket_name,
                exc_info=True
            )
            raise

        key = "%s.%s" % (crash_id, name_of_thing)

        storage_key = bucket.new_key(key)
        return storage_key.get_contents_as_string()

    #--------------------------------------------------------------------------
    def _connect(self):
        try:
            return self.connection
        except AttributeError:
            self.connection = self._connect_to_endpoint(
                aws_access_key_id=self.config.access_key,
                aws_secret_access_key=self.config.secret_access_key,
                host=self.config.host,
                port=self.config.port,
                is_secure=False,
                calling_format=self._calling_format(),
            )
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
        """ceph doesn't support transactions so this silently
        does nothing"""

    #--------------------------------------------------------------------------
    def rollback(self):
        """ceph doesn't support transactions so this silently
        does nothing"""

    #--------------------------------------------------------------------------
    @contextlib.contextmanager
    def __call__(self):
        """this class will serve as its own context manager.  That enables it
        to use the transaction_executor class for retries"""
        yield self

    #--------------------------------------------------------------------------
    def in_transaction(self, dummy):
        """ceph doesn't support transactions, so it is never in
        a transaction."""
        return False

    #--------------------------------------------------------------------------
    def is_operational_exception(self, msg):
        return False
    # Down to at least here^^^

    #--------------------------------------------------------------------------
    def force_reconnect(self):
        del self.connection
        self._bucket_cache = {}
