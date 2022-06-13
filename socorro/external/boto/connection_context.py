# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import io
import logging
import random
import time

import boto3
from botocore.client import ClientError
from configman import Namespace, RequiredConfig

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


class S3Connection(RequiredConfig):
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

    required_config = Namespace()
    required_config.add_option(
        "access_key",
        doc="access key",
        default=None,
        reference_value_from="resource.boto",
    )
    required_config.add_option(
        "secret_access_key",
        doc="secret access key",
        default=None,
        secret=True,
        reference_value_from="secrets.boto",
    )
    required_config.add_option(
        "bucket_name",
        doc="The name of the bucket.",
        default="crashstats",
        reference_value_from="resource.boto",
    )
    required_config.add_option(
        "region",
        doc="Name of the S3 region (e.g. us-west-2)",
        default="us-west-2",
        reference_value_from="resource.boto",
    )
    required_config.add_option(
        "s3_endpoint_url",
        doc=(
            "endpoint url to connect to; None if you are connecting to AWS. For "
            "example, ``http://localhost:4572/``."
        ),
        default="",
        reference_value_from="resource.boto",
    )

    KeyNotFound = KeyNotFound

    def __init__(self, config):
        self.config = config
        self.bucket = self.config.bucket_name
        self.client = self.build_client()

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
    def build_client(self):
        """Returns a Boto3 S3 Client."""
        # Either they provided ACCESS_KEY and SECRET_ACCESS_KEY in which case
        # we use those, or they didn't in which case boto3 pulls credentials
        # from one of a myriad of other places.
        # http://boto3.readthedocs.io/en/latest/guide/configuration.html#configuring-credentials
        session_kwargs = {}
        if self.config.access_key and self.config.secret_access_key:
            session_kwargs["aws_access_key_id"] = self.config.access_key
            session_kwargs["aws_secret_access_key"] = self.config.secret_access_key
        session = boto3.session.Session(**session_kwargs)

        kwargs = {
            "service_name": "s3",
            "region_name": self.config.region,
        }
        if self.config.s3_endpoint_url:
            kwargs["endpoint_url"] = self.config.s3_endpoint_url

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
    def save_file(self, path, data):
        """Save a single file to S3.

        This will retry a handful of times in short succession so as to deal
        with some amount of fishiness. After that, the caller should retry
        saving after a longer period of time.

        :arg str path: the path to save to

        :arg bytes data: the data to save

        :raises botocore.exceptions.ClientError: connection issues, permissions
            issues, bucket is missing, etc.

        """
        if not isinstance(data, bytes):
            raise TypeError("data argument must be bytes")

        self.client.upload_fileobj(
            Fileobj=io.BytesIO(data), Bucket=self.bucket, Key=path
        )

    @retry(
        retryable_exceptions=[
            # FIXME(willkg): Seems like botocore always raises ClientError
            # which is unhelpful for granularity purposes.
            ClientError
        ],
        wait_time_generator=wait_times_access,
        module_logger=logger,
    )
    def load_file(self, path):
        """Load a file from S3.

        This will retry a handful of times in short succession so as to deal
        with some amount of fishiness. After that, the caller should retry
        saving after a longer period of time.

        :arg str path: the path to save to

        :returns: bytes

        :raises botocore.exceptions.ClientError: connection issues, permissions
            issues, bucket is missing, etc.
        :raises KeyNotFound: if the key is not found

        """
        try:
            resp = self.client.get_object(Bucket=self.config.bucket_name, Key=path)
            return resp["Body"].read()
        except self.client.exceptions.NoSuchKey:
            raise KeyNotFound(
                "%s (bucket=%r key=%r) not found, no value returned"
                % (id, self.config.bucket_name, path)
            )
