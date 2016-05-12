# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import socket
import datetime
import contextlib

import boto
import boto.s3.connection
import boto.exception

from configman import Namespace, RequiredConfig, class_converter

from socorrolib.lib.converters import change_default
from socorrolib.lib.ooid import dateFromOoid


class KeyNotFound(Exception):
    pass


class JSONISOEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        raise NotImplementedError("Don't know about {0!r}".format(obj))


class KeyBuilderBase(object):
    """Base key builder for s3 pseudo-filenames"""
    def build_keys(self, prefix, name_of_thing, id):
        """
        Use S3 pseudo-directories to make it easier to list/expire later
        {prefix}/v1/{name_of_thing}/{id}
        """
        return [
            '%s/v1/%s/%s' % (prefix, name_of_thing, id)
        ]


class DatePrefixKeyBuilder(KeyBuilderBase):
    """s3 pseudo-filename key builder with date prefixes

    This adds the date to the prefix for raw_crash objects making it easier to
    list all the raw_crash objects for a specific date.

    """
    def build_keys(self, prefix, name_of_thing, id):
        """Use S3 pseudo-directories to make it easier to list/expire.

        For "raw_crash" things, the id is an ooid/crash_id. This uses the
        first three characters of the ooid for entropy and extracts the
        crash submission date from the last 6 charactes. Then it mooshes
        that all together into this structure::

            {prefix}/v2/{name_of_thing}/{entropy}/{date}/{id}

        This makes it possible to list all the raw_crashes submitted on a
        given date.

        It also returns the keys that KeyBuilderBase builds so that we can
        fetch objects that were saved with older keys.

        """
        keys = []

        if name_of_thing == 'raw_crash':
            datestamp = dateFromOoid(id)

            if datestamp is not None:
                # We insert the first 3 chars of the ooid/crash_id providing
                # some entropy earlier in the key so that consecutive s3
                # requests get distributed across multiple s3 partitions.
                first_chars = id[:3]
                date = datestamp.strftime('%Y%m%d')
                keys.append(
                    '%s/v2/%s/%s/%s/%s' % (
                        prefix, name_of_thing, first_chars, date, id
                    )
                )

        keys.extend(
            super(DatePrefixKeyBuilder, self).build_keys(
                prefix, name_of_thing, id
            )
        )
        return keys


#==============================================================================
class ConnectionContextBase(RequiredConfig):

    required_config = Namespace()
    required_config.add_option(
        'access_key',
        doc="access key",
        default="",
        reference_value_from='resource.boto',
    )
    required_config.add_option(
        'secret_access_key',
        doc="secret access key",
        default="",
        secret=True,
        reference_value_from='secrets.boto',
        likely_to_be_changed=True,
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
        default='',
        reference_value_from='resource.boto',
        likely_to_be_changed=True,
    )
    required_config.add_option(
        'keybuilder_class',
        default='socorro.external.boto.connection_context.KeyBuilderBase',
        doc=(
            'fully qualified dotted Python classname to handle building s3 '
            'pseudo-filenames'
        ),
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
        return False

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        self.config = config

        self._CreateError = boto.exception.StorageCreateError
        self.ResponseError = (
            boto.exception.StorageResponseError,
            KeyNotFound
        )
        self.keybuilder = config.keybuilder_class()

        self._bucket_cache = {}

    #--------------------------------------------------------------------------
    def _connect(self):
        try:
            return self.connection
        except AttributeError:
            self.connection = self._connect_to_endpoint(
                **self._get_credentials()
            )
            return self.connection

    #--------------------------------------------------------------------------
    def _get_credentials(self):
        """each subclass must implement this method to provide the type
        of credentials required for the type of connection"""
        raise NotImplementedError

    #--------------------------------------------------------------------------
    def build_keys(self, prefix, name_of_thing, id):
        """Builds an s3 pseudo-filename using the specified keybuilder class.

        """
        return self.keybuilder.build_keys(prefix, name_of_thing, id)

    #--------------------------------------------------------------------------
    def _get_bucket(self, conn, bucket_name):
        try:
            return self._bucket_cache[bucket_name]
        except KeyError:
            self._bucket_cache[bucket_name] = conn.get_bucket(bucket_name)
            return self._bucket_cache[bucket_name]

    #--------------------------------------------------------------------------
    def _get_or_create_bucket(self, conn, bucket_name):
        try:
            return self._get_bucket(conn, bucket_name)
        except self.ResponseError:
            self._bucket_cache[bucket_name] = conn.create_bucket(bucket_name)
            return self._bucket_cache[bucket_name]

    #--------------------------------------------------------------------------
    def submit(self, id, name_of_thing, thing):
        """submit something to boto.
        """
        # can only submit strings to boto
        assert isinstance(thing, basestring), type(thing)

        conn = self._connect()
        bucket = self._get_or_create_bucket(conn, self.config.bucket_name)

        all_keys = self.build_keys(self.config.prefix, name_of_thing, id)
        # Always submit using the first key
        key = all_keys[0]
        key_object = bucket.new_key(key)
        key_object.set_contents_from_string(thing)

    #--------------------------------------------------------------------------
    def fetch(self, id, name_of_thing):
        """retrieve something from boto.
        """
        conn = self._connect()
        bucket = self._get_bucket(conn, self.config.bucket_name)

        all_keys = self.build_keys(self.config.prefix, name_of_thing, id)
        for key in all_keys:
            key_object = bucket.get_key(key)
            if key_object is not None:
                return key_object.get_contents_as_string()

        # None of the keys worked, so raise an error
        raise KeyNotFound(
            '%s (bucket=%r keys=%r) not found, no value returned' % (
                id,
                self.config.bucket_name,
                all_keys,
            )
        )

    #--------------------------------------------------------------------------
    def _convert_mapping_to_string(self, a_mapping):
        return json.dumps(a_mapping, cls=JSONISOEncoder)

    #--------------------------------------------------------------------------
    def _convert_list_to_string(self, a_list):
        return json.dumps(a_list)

    #--------------------------------------------------------------------------
    def _convert_string_to_list(self, a_string):
        return json.loads(a_string)

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
class ConnectionContextWithHostAndPortBase(RequiredConfig):
    """an alternative base class that specific implementations of Boto
    connection can derive.  It adds "host" and "port" to the configuration"""

    required_config = Namespace()
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


#==============================================================================
class S3ConnectionContext(ConnectionContextBase):
    """This derived class includes the specifics for connection to S3"""
    required_config = Namespace()
    required_config.add_option(
        'calling_format',
        doc="fully qualified python path to the boto calling format function",
        default='boto.s3.connection.SubdomainCallingFormat',
        from_string_converter=class_converter,
        reference_value_from='resource.boto',
        likely_to_be_changed=True,
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(S3ConnectionContext, self).__init__(config)

        self._connect_to_endpoint = boto.connect_s3
        self._calling_format = config.calling_format

    #--------------------------------------------------------------------------
    def _get_credentials(self):
        return {
            'aws_access_key_id': self.config.access_key,
            'aws_secret_access_key': self.config.secret_access_key,
            'is_secure': True,
            'calling_format': self._calling_format(),
        }


#==============================================================================
class RegionalS3ConnectionContext(S3ConnectionContext):
    """This derviced class forces you to connect to a specific region
    which means we can use the OrdinaryCallingFormat as a calling format
    and then we'll be able to connect to S3 buckets with names in them.
    """
    required_config = Namespace()
    required_config.add_option(
        'region',
        doc="Name of the S3 region (e.g. us-west-2)",
        default='us-west-2',
        reference_value_from='resource.boto',
    )
    required_config.calling_format = change_default(
        S3ConnectionContext,
        'calling_format',
        'boto.s3.connection.OrdinaryCallingFormat'
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(RegionalS3ConnectionContext, self).__init__(config)
        self._region = config.region
        self._connect_to_endpoint = boto.s3.connect_to_region

    #--------------------------------------------------------------------------
    def _connect(self):
        try:
            return self.connection
        except AttributeError:
            self.connection = self._connect_to_endpoint(
                self._region,
                **self._get_credentials()
            )
            return self.connection
