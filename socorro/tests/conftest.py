# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
pytest plugins for socorro/tests/ and webapp/ test suites.
"""

import datetime
import io
import logging
import os
import pathlib
import uuid
import sys

import boto3
from botocore.client import ClientError, Config
from elasticsearch_dsl import Search
from google.api_core.exceptions import AlreadyExists, NotFound
from google.auth.credentials import AnonymousCredentials
from google.cloud import storage
from google.cloud.pubsub_v1 import PublisherClient, SubscriberClient
from google.cloud.pubsub_v1.types import BatchSettings, PublisherOptions
from markus.testing import MetricsMock
import pytest
import requests_mock

from socorro import settings
from socorro.libclass import build_instance_from_settings
from socorro.lib.libdatetime import utc_now
from socorro.lib.libooid import create_new_ooid, date_from_ooid


REPOROOT = pathlib.Path(__file__).parent.parent.parent


# Add bin directory to Python path
sys.path.insert(0, str(REPOROOT / "bin"))


@pytest.fixture
def reporoot():
    """Returns path to repository root directory"""
    return REPOROOT


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


class DebugIdHelper:
    """Breakpad debug id helper class."""

    def generate(self):
        """Returns 33-character uppercase hex string"""
        return uuid.uuid4().hex.upper() + "A"


@pytest.fixture
def debug_id_helper():
    yield DebugIdHelper()


class S3Helper:
    """S3 helper class.

    When used in a context, this will clean up any buckets created.

    """

    def __init__(self):
        self._buckets_seen = None
        self.conn = self.get_client()

    def get_client(self):
        session = boto3.session.Session(
            # NOTE(willkg): these use environment variables set in
            # docker/config/test.env
            aws_access_key_id=os.environ["CRASHSTORAGE_S3_ACCESS_KEY"],
            aws_secret_access_key=os.environ["CRASHSTORAGE_S3_SECRET_ACCESS_KEY"],
        )
        client = session.client(
            service_name="s3",
            config=Config(s3={"addressing_style": "path"}),
            endpoint_url=os.environ["LOCAL_DEV_AWS_ENDPOINT_URL"],
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

    def get_crashstorage_bucket(self):
        return os.environ["CRASHSTORAGE_S3_BUCKET"]

    def get_telemetry_bucket(self):
        return os.environ["TELEMETRY_S3_BUCKET"]

    def create_bucket(self, bucket_name):
        """Create specified bucket if it doesn't exist."""
        try:
            self.conn.head_bucket(Bucket=bucket_name)
        except ClientError:
            self.conn.create_bucket(Bucket=bucket_name)
        if self._buckets_seen is not None:
            self._buckets_seen.add(bucket_name)

    def upload(self, bucket_name, key, data):
        """Puts an object into the specified bucket."""
        self.create_bucket(bucket_name)
        self.conn.upload_fileobj(Fileobj=io.BytesIO(data), Bucket=bucket_name, Key=key)

    def download(self, bucket_name, key):
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
def s3_helper():
    """Returns an S3Helper for automating repetitive tasks in S3 setup.

    Provides:

    * ``get_client()``
    * ``get_crashstorage_bucket()``
    * ``create_bucket(bucket_name)``
    * ``upload(bucket_name, key, data)``
    * ``download(bucket_name, key)``
    * ``list(bucket_name)``

    """
    with S3Helper() as s3_helper:
        yield s3_helper


class GcsHelper:
    """GCS helper class.

    When used in a context, this will clean up any buckets created.

    """

    def __init__(self):
        self._buckets_seen = None
        if os.environ.get("STORAGE_EMULATOR_HOST"):
            self.client = storage.Client(
                credentials=AnonymousCredentials(),
                project="test",
            )
        else:
            self.client = storage.Client()

    def __enter__(self):
        self._buckets_seen = set()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        for bucket_name in self._buckets_seen:
            try:
                bucket = self.client.get_bucket(bucket_or_name=bucket_name)
                bucket.delete(force=True)
            except NotFound:
                pass
        self._buckets_seen = None

    def get_crashstorage_bucket(self):
        return os.environ["CRASHSTORAGE_GCS_BUCKET"]

    def get_telemetry_bucket(self):
        return os.environ["TELEMETRY_GCS_BUCKET"]

    def create_bucket(self, bucket_name):
        """Create specified bucket if it doesn't exist."""
        try:
            bucket = self.client.get_bucket(bucket_or_name=bucket_name)
        except NotFound:
            bucket = self.client.create_bucket(bucket_or_name=bucket_name)
        if self._buckets_seen is not None:
            self._buckets_seen.add(bucket_name)
        return bucket

    def upload(self, bucket_name, key, data):
        """Puts an object into the specified bucket."""
        bucket = self.create_bucket(bucket_name)
        bucket.blob(blob_name=key).upload_from_string(data)

    def download(self, bucket_name, key):
        """Fetches an object from the specified bucket"""
        bucket = self.create_bucket(bucket_name)
        return bucket.blob(blob_name=key).download_as_bytes()

    def list(self, bucket_name):
        """Return list of keys for objects in bucket."""
        self.create_bucket(bucket_name)
        blobs = list(self.client.list_blobs(bucket_or_name=bucket_name))
        return [blob.name for blob in blobs]


@pytest.fixture
def gcs_helper():
    """Returns an GcsHelper for automating repetitive tasks in GCS setup.

    Provides:

    * ``get_crashstorage_bucket()``
    * ``get_telemetry_bucket()``
    * ``create_bucket(bucket_name)``
    * ``upload(bucket_name, key, data)``
    * ``download(bucket_name, key)``
    * ``list(bucket_name)``

    """
    with GcsHelper() as gcs_helper:
        yield gcs_helper


class ElasticsearchHelper:
    """Elasticsearch helper class.

    When used in a context, this will clean up any indexes created.

    """

    def __init__(self):
        self._crashstorage = build_instance_from_settings(settings.ES_STORAGE)
        self.conn = self._crashstorage.client

    def get_index_template(self):
        return self._crashstorage.get_index_template()

    def get_doctype(self):
        return self._crashstorage.get_doctype()

    def create_index(self, index_name):
        print(f"ElasticsearchHelper: creating index: {index_name}")
        self._crashstorage.create_index(index_name)

    def create_indices(self):
        # Create all the indexes for the last couple of weeks; we have to do it this way
        # to handle split indexes over the new year
        template = self._crashstorage.index
        to_create = set()

        for i in range(14):
            index_name = (utc_now() - datetime.timedelta(days=i)).strftime(template)
            to_create.add(index_name)

        for index_name in to_create:
            print(f"ElasticsearchHelper: creating index: {index_name}")
            self._crashstorage.create_index(index_name)

        self.health_check()

    def delete_indices(self):
        for index in self._crashstorage.get_indices():
            self._crashstorage.delete_index(index)

    def get_indices(self):
        return self._crashstorage.get_indices()

    def health_check(self):
        with self.conn() as conn:
            conn.cluster.health(wait_for_status="yellow", request_timeout=5)

    def get_url(self):
        """Returns the Elasticsearch url."""
        return settings.ES_STORAGE["options"]["url"]

    def refresh(self):
        self.conn.refresh()

    def index_crash(self, processed_crash, refresh=True):
        """Index a single crash and refresh"""
        self._crashstorage.save_processed_crash(
            raw_crash={},
            processed_crash=processed_crash,
        )

        if refresh:
            self.refresh()

    def index_many_crashes(self, number, processed_crash=None, loop_field=None):
        """Index multiple crashes and refresh at the end"""
        processed_crash = processed_crash or {}

        crash_ids = []
        for i in range(number):
            processed_copy = processed_crash.copy()
            processed_copy["uuid"] = create_new_ooid()
            processed_copy["date_processed"] = date_from_ooid(processed_copy["uuid"])
            if loop_field is not None:
                processed_copy[loop_field] = processed_crash[loop_field] % i

            self.index_crash(processed_crash=processed_copy, refresh=False)

        self.refresh()
        return crash_ids

    def get_crash_data(self, crash_id):
        """Get source in index for given crash_id

        :arg crash_id: the crash id to fetch the source for

        :returns: source as a Python dict

        """
        index = self._crashstorage.get_index_for_date(date_from_ooid(crash_id))
        doc_type = self._crashstorage.get_doctype()

        with self.conn() as conn:
            search = Search(using=conn, index=index, doc_type=doc_type)
            search = search.filter("term", **{"processed_crash.uuid": crash_id})
            results = search.execute().to_dict()

            return results["hits"]["hits"][0]["_source"]


@pytest.fixture
def es_helper():
    """Returns an ElasticsearchHelper for helping tests.

    Provides:

    * ``get_doctype()``
    * ``get_url()``
    * ``create_indices()``
    * ``delete_indices()``
    * ``get_indices()``
    * ``index_crash()``
    * ``index_many_crashes()``
    * ``refresh()``
    * ``get_crash_data()``

    """
    es_helper = ElasticsearchHelper()
    es_helper.create_indices()
    yield es_helper
    es_helper.delete_indices()


class SQSHelper:
    """Helper class for setting up, tearing down, and publishing to SQS."""

    def __init__(self):
        self.conn = self.get_client()

        self.queue_to_queue_name = {
            "standard": os.environ["SQS_STANDARD_QUEUE"],
            "priority": os.environ["SQS_PRIORITY_QUEUE"],
            "reprocessing": os.environ["SQS_REPROCESSING_QUEUE"],
        }

        self.conn = self.get_client()

        # Visibility timeout for the AWS SQS queue in seconds
        self.visibility_timeout = 1

    def get_client(self):
        session = boto3.session.Session(
            # NOTE(willkg): these use environment variables set in
            # docker/config/test.env
            aws_access_key_id=os.environ["SQS_ACCESS_KEY"],
            aws_secret_access_key=os.environ["SQS_SECRET_ACCESS_KEY"],
        )
        client = session.client(
            service_name="sqs",
            region_name=os.environ["SQS_REGION"],
            endpoint_url=os.environ["LOCAL_DEV_AWS_ENDPOINT_URL"],
        )
        return client

    def setup_queues(self):
        for queue_name in self.queue_to_queue_name.values():
            self.create_queue(queue_name)

    def teardown_queues(self):
        for queue_name in self.queue_to_queue_name.values():
            try:
                queue_url = self.conn.get_queue_url(QueueName=queue_name)["QueueUrl"]
                self.conn.delete_queue(QueueUrl=queue_url)
            except self.conn.exceptions.QueueDoesNotExist:
                print(f"skipping teardown {queue_name!r}: does not exist")

    def __enter__(self):
        self.setup_queues()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.teardown_queues()

    def create_queue(self, queue_name):
        self.conn.create_queue(
            QueueName=queue_name,
            Attributes={"VisibilityTimeout": str(self.visibility_timeout)},
        )

    def get_published_crashids(self, queue):
        queue_name = self.queue_to_queue_name[queue]
        queue_url = self.conn.get_queue_url(QueueName=queue_name)["QueueUrl"]
        all_crashids = []
        while True:
            resp = self.conn.receive_message(
                QueueUrl=queue_url,
                WaitTimeSeconds=0,
                VisibilityTimeout=1,
            )
            msgs = resp.get("Messages", [])
            if not msgs:
                break
            all_crashids.extend([msg["Body"] for msg in msgs])

        return all_crashids

    def publish(self, queue, crash_id):
        queue_name = self.queue_to_queue_name[queue]
        queue_url = self.conn.get_queue_url(QueueName=queue_name)["QueueUrl"]
        self.conn.send_message(QueueUrl=queue_url, MessageBody=crash_id)


@pytest.fixture
def sqs_helper():
    with SQSHelper() as sqs:
        yield sqs


class PubSubHelper:
    """Helper class for setting up, tearing down, and publishing to Pub/Sub."""

    def __init__(self):
        self.publisher = PublisherClient(
            # publish messages immediately without queuing
            batch_settings=BatchSettings(max_messages=1),
            # disable retry and set short rpc timeout
            publisher_options=PublisherOptions(retry=None, timeout=1),
        )
        self.subscriber = SubscriberClient()

        self.project_id = os.environ["PUBSUB_PROJECT_ID"]

        self.queue_to_topic_name = {
            "standard": os.environ["PUBSUB_STANDARD_TOPIC_NAME"],
            "priority": os.environ["PUBSUB_PRIORITY_TOPIC_NAME"],
            "reprocessing": os.environ["PUBSUB_REPROCESSING_TOPIC_NAME"],
        }

        self.queue_to_subscription_name = {
            "standard": os.environ["PUBSUB_STANDARD_SUBSCRIPTION_NAME"],
            "priority": os.environ["PUBSUB_PRIORITY_SUBSCRIPTION_NAME"],
            "reprocessing": os.environ["PUBSUB_REPROCESSING_SUBSCRIPTION_NAME"],
        }

        # Ack deadline for the Pub/Sub subscription in seconds
        if os.environ.get("PUBSUB_EMULATOR_HOST"):
            # emulator allows smaller deadline than actual Pub/Sub
            self.ack_deadline_seconds = 1
        else:
            # Pub/Sub's minimum value for this is 10 seconds
            # https://cloud.google.com/pubsub/docs/subscription-properties#ack_deadline
            self.ack_deadline_seconds = 10

    def setup_queues(self):
        for queue in self.queue_to_topic_name.keys():
            self.create_queue(queue)

    def teardown_queues(self):
        for subscription_name in self.queue_to_subscription_name.values():
            subscription_path = self.subscriber.subscription_path(
                self.project_id, subscription_name
            )
            try:
                self.subscriber.delete_subscription(subscription=subscription_path)
            except NotFound:
                print(
                    f"skipping teardown subscription {subscription_name!r}: does not exist"
                )
        for topic_name in self.queue_to_topic_name.values():
            topic_path = self.publisher.topic_path(self.project_id, topic_name)
            try:
                self.publisher.delete_topic(topic=topic_path)
            except NotFound:
                print(f"skipping teardown topic {topic_name!r}: does not exist")

    def __enter__(self):
        self.setup_queues()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.teardown_queues()

    def create_queue(self, queue):
        topic_name = self.queue_to_topic_name[queue]
        topic_path = self.publisher.topic_path(self.project_id, topic_name)
        try:
            self.publisher.create_topic(name=topic_path)
        except AlreadyExists:
            pass  # that's fine
        subscription_name = self.queue_to_subscription_name[queue]
        subscription_path = self.subscriber.subscription_path(
            self.project_id, subscription_name
        )
        try:
            self.subscriber.get_subscription(subscription=subscription_path)
        except NotFound:
            pass  # good
        else:
            # recreate it to drop any prior messages
            self.subscriber.delete_subscription(subscription=subscription_path)
        self.subscriber.create_subscription(
            name=subscription_path,
            topic=topic_path,
            ack_deadline_seconds=self.ack_deadline_seconds,
        )

    def get_published_crashids(self, queue, max_messages=5):
        subscription_name = self.queue_to_subscription_name[queue]
        subscription_path = self.subscriber.subscription_path(
            self.project_id, subscription_name
        )
        all_crashids = []
        while True:
            resp = self.subscriber.pull(
                subscription=subscription_path,
                max_messages=max_messages,
            )
            msgs = resp.received_messages
            all_crashids.extend([msg.message.data.decode("utf-8") for msg in msgs])
            if len(msgs) < max_messages:
                break

        return all_crashids

    def publish(self, queue, crash_id):
        topic_name = self.queue_to_topic_name[queue]
        topic_path = self.publisher.topic_path(self.project_id, topic_name)
        self.publisher.publish(topic=topic_path, data=crash_id.encode("utf-8"))


@pytest.fixture
def pubsub_helper():
    with PubSubHelper() as pubsub:
        yield pubsub


@pytest.fixture(
    # define these params once and reference this fixture to prevent undesirable
    # combinations, i.e. tests marked with aws *and* gcp for pubsub+s3 or sqs+gcs
    params=[
        # tests that require a specific cloud provider backend must be marked with that
        # provider, and non-default backends must be excluded by default, for example
        # via pytest.ini's addopts, i.e. addopts = -m 'not gcp'
        pytest.param("aws", marks=pytest.mark.aws),
        pytest.param("gcp", marks=pytest.mark.gcp),
    ]
)
def cloud_provider(request):
    return request.param


@pytest.fixture
def queue_helper(cloud_provider):
    """Generate and return a queue helper using env config."""
    actual_backend = "sqs"
    if os.environ.get("CLOUD_PROVIDER", "").strip().upper() == "GCP":
        actual_backend = "pubsub"

    expect_backend = "pubsub" if cloud_provider == "gcp" else "sqs"
    if actual_backend != expect_backend:
        pytest.fail(f"test requires {expect_backend} but found {actual_backend}")

    if actual_backend == "pubsub":
        helper = PubSubHelper()
    else:
        helper = SQSHelper()

    with helper as _helper:
        yield _helper


@pytest.fixture
def storage_helper(cloud_provider):
    """Generate and return a queue helper using env config."""
    actual_backend = "s3"
    if os.environ.get("CLOUD_PROVIDER", "").strip().upper() == "GCP":
        actual_backend = "gcs"

    expect_backend = "gcs" if cloud_provider == "gcp" else "s3"
    if actual_backend != expect_backend:
        pytest.fail(f"test requires {expect_backend} but found {actual_backend}")

    if actual_backend == "gcs":
        helper = GcsHelper()
    else:
        helper = S3Helper()

    with helper as _helper:
        yield _helper
