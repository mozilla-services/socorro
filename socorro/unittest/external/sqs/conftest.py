# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import boto3
import pytest

from socorro.unittest.external.sqs import get_sqs_config


# Socorro uses three queues. Each is implemented as a SQS queue.
QUEUES = ["standard", "priority", "reprocessing"]


class SQSHelper:
    """Helper class for setting up, tearing down, and publishing to Pub/Sub.

    Note: This uses the same config as SQSCrashQueue.

    """

    def __init__(self, config):
        self.config = config
        self.client = self.build_client()
        self._queues = []

        self.queue_to_queue_name = {
            "standard": self.config.standard_queue,
            "priority": self.config.priority_queue,
            "reprocessing": self.config.reprocessing_queue,
        }

    def build_client(self):
        session = boto3.session.Session(
            aws_access_key_id=self.config.access_key,
            aws_secret_access_key=self.config.secret_access_key,
        )
        client = session.client(
            service_name="sqs",
            region_name=self.config.region,
            endpoint_url=self.config.sqs_endpoint_url,
        )
        return client

    def setup_queues(self):
        for queue_name in self.queue_to_queue_name.values():
            self.create_queue(queue_name)

    def teardown_queues(self):
        for queue_name in self._queues:
            queue_url = self.client.get_queue_url(QueueName=queue_name)["QueueUrl"]
            self.client.delete_queue(QueueUrl=queue_url)

    def __enter__(self):
        self.setup_queues()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.teardown_queues()

    def create_queue(self, queue_name):
        self.client.create_queue(QueueName=queue_name)
        self._queues.append(queue_name)

    def get_published_crashids(self, queue):
        queue_name = self.queue_to_queue_name[queue]
        queue_url = self.client.get_queue_url(QueueName=queue_name)["QueueUrl"]
        all_crashids = []
        while True:
            resp = self.client.receive_message(
                QueueUrl=queue_url, WaitTimeSeconds=0, VisibilityTimeout=1,
            )
            msgs = resp.get("Messages", [])
            if not msgs:
                break
            all_crashids.extend([msg["Body"] for msg in msgs])

        return all_crashids

    def publish(self, queue, crash_id):
        queue_name = self.queue_to_queue_name[queue]
        queue_url = self.client.get_queue_url(QueueName=queue_name)["QueueUrl"]
        self.client.send_message(QueueUrl=queue_url, MessageBody=crash_id)


@pytest.yield_fixture
def sqs_helper():
    config = get_sqs_config()
    with SQSHelper(config) as sqs:
        yield sqs
