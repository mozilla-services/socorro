# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import io
import logging
import random
import time

import boto3
from botocore.client import ClientError

from socorro.lib.util import retry


logger = logging.getLogger(__name__)


def wait_times_connect():
    """Return generator for wait times between failed connection attempts.

    We have this problem where we're binding IAM credentials to the EC2 node
    and on startup when boto3 goes to get the credentials, it fails for some
    reason and then degrades to hitting the https://s3..amazonaws.net/
    endpoint and then fails because that's not a valid endpoint.

    This sequence increases the wait times and adds some jitter.

    """
    for i in [5, 5, 5, 5, 5]:
        yield i + random.uniform(-2, 2)  # nosec


def wait_times_access():
    """Return generator for wait times between failed load/save attempts."""
    yield from [1, 1, 1, 1, 1]


class KeyNotFound(Exception):
    pass


class S3Connection:
    """Connection object for S3.

    **Credentials and permissions**

    When configuring this connection object, you can do one of two things:

    1. provide ``ACCESS_KEY`` and ``SECRET_ACCESS_KEY`` in the configuration, OR
    2. use one of the other methods described in the boto3 docs
       http://boto3.readthedocs.io/en/latest/guide/configuration.html#configuring-credentials

    The AWS credentials that Socorro is configured with must have the following
    Amazon S3 permissions:

    * ``s3:ListBucket``: Socorro lists contents of the bucket.
    * ``s3:PutObject``: Socorro saves crash data in the bucket.
    * ``s3:GetObject``: Socorro retrieves crash data from buckets.

    **Retrying loads and saves**

    When loading and saving crashes, this connection will retry several times.

    """

    # Attach to class so it's easier to access without imports
    KeyNotFound = KeyNotFound

    def __init__(
        self,
        region=None,
        access_key=None,
        secret_access_key=None,
        endpoint_url=None,
        **kwargs,
    ):
        """
        :arg region: AWS region to use (e.g. us-west-2)
        :arg access_key: AWS access key
        :arg secret_access_key: AWS secret access key
        :arg endpoint_url: the endpoint url to use when in a local development
            environment
        """

        self.region = region
        self.client = self.build_client(
            region=region,
            access_key=access_key,
            secret_access_key=secret_access_key,
            endpoint_url=endpoint_url,
        )

    @retry(
        retryable_exceptions=[
            # FIXME(willkg): Seems like botocore always raises ClientError
            # which is unhelpful for granularity purposes.
            ClientError,
            # This raises a ValueError "invalid endpoint" if it has problems
            # getting the s3 credentials and then tries "s3..amazonaws.com"--we
            # want to retry that, too.
            ValueError,
        ],
        wait_time_generator=wait_times_connect,
        sleep_function=time.sleep,
        module_logger=logger,
    )
    def build_client(
        cls,
        region,
        access_key=None,
        secret_access_key=None,
        endpoint_url=None,
        **kwargs,
    ):
        """Returns a Boto3 S3 Client.

        :arg region: the S3 region to use
        :arg access_key: the S3 access_key to use
        :arg secret_access_key: the S3 secret_access_key to use
        :arg endpoint_url: the endpoint url to use when in a local development
            environment

        """
        # Either they provided ACCESS_KEY and SECRET_ACCESS_KEY in which case
        # we use those, or they didn't in which case boto3 pulls credentials
        # from one of a myriad of other places.
        # http://boto3.readthedocs.io/en/latest/guide/configuration.html#configuring-credentials
        session_kwargs = {}
        if access_key and secret_access_key:
            session_kwargs["aws_access_key_id"] = access_key
            session_kwargs["aws_secret_access_key"] = secret_access_key
        session = boto3.session.Session(**session_kwargs)

        kwargs = {
            "service_name": "s3",
            "region_name": region,
        }
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url

        return session.client(**kwargs)

    @retry(
        retryable_exceptions=[
            # FIXME(willkg): Seems like botocore always raises ClientError
            # which is unhelpful for granularity purposes.
            ClientError
        ],
        wait_time_generator=wait_times_access,
        module_logger=logger,
    )
    def save_file(self, bucket, path, data):
        """Save a single file to S3.

        This will retry a handful of times in short succession so as to deal
        with some amount of fishiness. After that, the caller should retry
        saving after a longer period of time.

        :arg str bucket: the bucket to save to
        :arg str path: the path to save to
        :arg bytes data: the data to save

        :raises botocore.exceptions.ClientError: connection issues, permissions
            issues, bucket is missing, etc.

        """
        if not isinstance(data, bytes):
            raise TypeError("data argument must be bytes")

        self.client.upload_fileobj(Fileobj=io.BytesIO(data), Bucket=bucket, Key=path)

    @retry(
        retryable_exceptions=[
            # FIXME(willkg): Seems like botocore always raises ClientError
            # which is unhelpful for granularity purposes.
            ClientError
        ],
        wait_time_generator=wait_times_access,
        module_logger=logger,
    )
    def load_file(self, bucket, path):
        """Load a file from S3.

        This will retry a handful of times in short succession so as to deal with some
        amount of fishiness. After that, the caller should retry saving after a longer
        period of time.

        :arg str bucket: the bucket to load from
        :arg str path: the path to load from

        :returns: bytes

        :raises botocore.exceptions.ClientError: connection issues, permissions
            issues, bucket is missing, etc.
        :raises KeyNotFound: if the key is not found

        """
        try:
            resp = self.client.get_object(Bucket=bucket, Key=path)
            return resp["Body"].read()
        except self.client.exceptions.NoSuchKey:
            raise KeyNotFound(
                f"(bucket={bucket!r} key={path}) not found, no value returned"
            )

    def list_objects_paginator(self, bucket, prefix):
        """Returns S3 client paginator of objects with key prefix in bucket

        :arg bucket: the name of the bucket
        :arg prefix: the key prefix

        :returns: S3 paginator

        """
        paginator = self.client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
        return page_iterator

    def head_object(self, bucket, key):
        """HEAD action on an object in a S3 bucket

        :arg bucket: the name of the bucket
        :arg key: the key for the object to HEAD

        :returns: S3 HEAD response

        :raises KeyNotFound: if the object doesn't exist
        :raises botocore.exceptions.ClientError: connection issues, permissions
            issues, bucket is missing, etc.

        """
        try:
            return self.client.head_object(Bucket=bucket, Key=key)
        except self.client.exceptions.NoSuchKey:
            raise KeyNotFound(
                f"(bucket={bucket!r} key={key}) not found, no value returned"
            )
