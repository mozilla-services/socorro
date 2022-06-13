# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
pytest plugins for socorro/unittest/ and webapp-django/ test suites.
"""

import datetime
import io
import logging
import os
import pathlib

import boto3
from botocore.client import ClientError, Config
from configman import ConfigurationManager
from configman.environment import environment
from markus.testing import MetricsMock
import pytest
import requests_mock

from socorro.external.es.connection_context import (
    ConnectionContext as ESConnectionContext,
)
from socorro.lib.libdatetime import utc_now


@pytest.fixture
def reporoot():
    """Returns path to repository root directory"""
    path = pathlib.Path(__file__).parent.parent.parent
    return path


@pytest.fixture
def req_mock():
    """Return requests mock."""
    with requests_mock.mock() as mock:
        yield mock


@pytest.fixture
def metricsmock():
    """Return MetricsMock that a context to record metrics records.

    Usage::

        def test_something(metricsmock):
            with metricsmock as mm:
                # do stuff
                mm.assert_incr("some.stat", value=1)


    https://markus.readthedocs.io/en/latest/testing.html

    """
    return MetricsMock()


@pytest.fixture
def caplogpp(caplog):
    """Fix logger propagation values, return caplog fixture, and unfix when done."""
    changed_loggers = []
    for logger in logging.Logger.manager.loggerDict.values():
        if getattr(logger, "propagate", True) is False:
            logger.propagate = True
            changed_loggers.append(logger)

    yield caplog

    for logger in changed_loggers:
        logger.propagate = False


class BotoHelper:
    """Helper class inspired by Boto's S3 API.

    The goal here is to automate repetitive things in a convenient way, but
    be inspired by the existing Boto S3 API.

    When used in a context, this will clean up any buckets created.

    """

    def __init__(self):
        self._buckets_seen = None
        self.conn = self.get_client()

    def get_client(self):
        session = boto3.session.Session(
            aws_access_key_id=os.environ.get("resource.boto.access_key"),
            aws_secret_access_key=os.environ.get("secrets.boto.secret_access_key"),
        )
        client = session.client(
            service_name="s3",
            config=Config(s3={"addressing_style": "path"}),
            endpoint_url=os.environ.get("resource.boto.s3_endpoint_url"),
        )
        return client

    def __enter__(self):
        self._buckets_seen = set()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        for bucket in self._buckets_seen:
            # Delete any objects in the bucket
            resp = self.conn.list_objects(Bucket=bucket)
            for obj in resp.get("Contents", []):
                key = obj["Key"]
                self.conn.delete_object(Bucket=bucket, Key=key)

            # Then delete the bucket
            self.conn.delete_bucket(Bucket=bucket)
        self._buckets_seen = None

    def create_bucket(self, bucket_name):
        """Create specified bucket if it doesn't exist."""
        try:
            self.conn.head_bucket(Bucket=bucket_name)
        except ClientError:
            self.conn.create_bucket(Bucket=bucket_name)
        if self._buckets_seen is not None:
            self._buckets_seen.add(bucket_name)

    def upload_fileobj(self, bucket_name, key, data):
        """Puts an object into the specified bucket."""
        self.create_bucket(bucket_name)
        self.conn.upload_fileobj(Fileobj=io.BytesIO(data), Bucket=bucket_name, Key=key)

    def download_fileobj(self, bucket_name, key):
        """Fetches an object from the specified bucket"""
        self.create_bucket(bucket_name)
        resp = self.conn.get_object(Bucket=bucket_name, Key=key)
        return resp["Body"].read()

    def list(self, bucket_name):
        """Return list of keys for objects in bucket."""
        self.create_bucket(bucket_name)
        resp = self.conn.list_objects(Bucket=bucket_name)
        return [obj["Key"] for obj in resp["Contents"]]


@pytest.fixture
def boto_helper():
    """Returns a BotoHelper for automating repetitive tasks in S3 setup.

    Provides:

    * ``get_client()``
    * ``create_bucket(bucket_name)``
    * ``upload_fileobj(bucket_name, key, value)``
    * ``download_fileobj(bucket_name, key)``
    * ``list(bucket_name)``

    """
    with BotoHelper() as boto_helper:
        yield boto_helper


@pytest.fixture
def es_conn():
    """Create an Elasticsearch ConnectionContext and clean up indices afterwards.

    This uses defaults and configuration from the environment.

    """
    manager = ConfigurationManager(
        ESConnectionContext.get_required_config(), values_source_list=[environment]
    )
    conn = ESConnectionContext(manager.get_config())

    # Create all the indexes for the last couple of weeks; we have to do it this way to
    # handle split indexes over the new year
    template = conn.config.elasticsearch_index
    to_create = set()

    for i in range(14):
        index_name = (utc_now() - datetime.timedelta(days=i)).strftime(template)
        to_create.add(index_name)

    for index_name in to_create:
        print(f"es_conn: creating index: {index_name}")
        conn.create_index(index_name)

    conn.health_check()

    yield conn

    for index in conn.get_indices():
        conn.delete_index(index)
