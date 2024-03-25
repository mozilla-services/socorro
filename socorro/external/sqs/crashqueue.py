# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from functools import partial
import logging
import random
import time

import boto3
from botocore.client import ClientError
from more_itertools import chunked

from socorro.external.crashqueue_base import CrashQueueBase
from socorro.lib.util import retry


# Maximum number of messages to pull from an SQS queue in a single pull request
SQS_MAX_MESSAGES = 5


logger = logging.getLogger(__name__)


class CrashIdsFailedToPublish(Exception):
    """Crash ids that failed to publish."""


class InvalidQueueName(Exception):
    """Denotes an invalid queue name."""


def wait_times_connect():
    """Return generator for wait times with jitter between failed connection attempts."""
    for i in [5] * 5:
        yield i + random.uniform(-2, 2)  # nosec


class SQSCrashQueue(CrashQueueBase):
    """Crash queue that uses AWS SQS.

    This requires three AWS SQS queues:

    * **standard queue**: processing incoming crashes from the collector
    * **priority queue**: processing crashes right now because someone/something
      is trying to view them
    * **reprocessing queue**: reprocessing crashes after a change to the processor
      that have (probably) already been processed

    When configuring credentials for this crashqueue object, you can do one of two
    things:

    1. provide ``ACCESS_KEY`` and ``SECRET_ACCESS_KEY`` in the configuration, OR
    2. use one of the other methods described in the boto3 docs
       http://boto3.readthedocs.io/en/latest/guide/configuration.html#configuring-credentials

    You also need to have three AWS SQS queues:

    * standard
    * priority
    * reprocessing

    and they need the following settings:

    ==========================  =========
    Setting                     Value
    ==========================  =========
    Default Visibility Timeout  5 minutes
    Message Retention Period    *default*
    Maximum Message Size        *default*
    Delivery Delay              *default*
    Receive Message Wait Time   *default*
    ==========================  =========

    The AWS credentials that Socorro is configured with must have the following
    Amazon SQS permissions on the SQS queue you created:

    * ``sqs:GetQueueUrl``

      Socorro needs to convert a queue name to a queue url. This requires the
      ``sqs:GetQueueUrl``

    * ``sqs:SendMessage``

      Socorro sends messages to a queue--this is how the webapp publishes crash ids
      to the priority and reprocessing queues. This requires the ``sqs:SendMessage``
      permission.

    * ``sqs:DeleteMessage``

      Once Socorro processor has processed a crash report, it needs to delete the
      message from the queue. This requires the ``sqs:DeleteMessage`` permission.

    * ``sqs:ReceiveMessage``

      The Socorro processor has to receive messages from the queue in order to
      process the related crash reports. This requires the ``sqs:ReceiveMessage``
      permission.

    If something isn't configured correctly, then the Socorro processor will be unable
    to process crashes and the webapp will be unable to publish crash ids for
    processing.

    """

    def __init__(
        self,
        standard_queue,
        priority_queue,
        reprocessing_queue,
        region,
        max_messages=SQS_MAX_MESSAGES,
        access_key=None,
        secret_access_key=None,
        endpoint_url=None,
    ):
        """
        :arg standard_queue: name for the standard SQS queue
        :arg priority_queue: name for the priority SQS queue
        :arg reprocessing_queue: name for the reprocessing SQS queue
        :arg region: the AWS region to use
        :arg access_key: the AWS access_key to use
        :arg secret_access_key: the AWS secret_access_key to use
        :arg endpoint_url: the endpoint url to use when in a local development
            environment
        """

        self.client = self.build_client(
            region=region,
            access_key=access_key,
            secret_access_key=secret_access_key,
            endpoint_url=endpoint_url,
        )

        self.standard_queue_url = self.get_queue_url(standard_queue)
        self.priority_queue_url = self.get_queue_url(priority_queue)
        self.reprocessing_queue_url = self.get_queue_url(reprocessing_queue)
        self.queue_to_queue_url = {
            "standard": self.standard_queue_url,
            "priority": self.priority_queue_url,
            "reprocessing": self.reprocessing_queue_url,
        }
        self.max_messages = max_messages

    @classmethod
    def validate_queue_name(cls, queue_name):
        """Validates a queue name

        :arg queue_name: the queue name to validate

        :raises InvalidQueueName: if the queue name is invalid, this is raised with
            details

        """
        if len(queue_name) > 80:
            raise InvalidQueueName("queue name is too long.")

        for c in queue_name:
            if not c.isalnum() and c not in "-_":
                raise InvalidQueueName(
                    f"queue name {queue_name!r} invalid: {c!r} is not an "
                    + "alphanumeric, - or _ character."
                )

    @classmethod
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
        """Returns a Boto3 SQS Client."""
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
            "service_name": "sqs",
            "region_name": region,
        }
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url

        return session.client(**kwargs)

    def get_queue_url(self, queue_name):
        """Returns the SQS queue url for the given queue name

        :arg queue_name: the queue name

        :returns: the url for the queue

        """
        return self.client.get_queue_url(QueueName=queue_name)["QueueUrl"]

    def ack_crash(self, queue_url, handle):
        """Acknowledges a crash

        :arg queue_url: the url for the queue
        :arg handle: the handle for the item to acknowledge

        """
        self.client.delete_message(QueueUrl=queue_url, ReceiptHandle=handle)
        logger.debug("ack %s from %s", handle, queue_url)

    def __iter__(self):
        """Return iterator over crash ids from AWS SQS.

        Each returned crash is a ``(crash_id, {kwargs})`` tuple with
        ``finished_func`` as the only key in ``kwargs``. The caller should call
        ``finished_func`` when it's done processing the crash.

        """
        queue_urls = [
            self.priority_queue_url,
            self.standard_queue_url,
            self.reprocessing_queue_url,
        ]

        while True:
            has_msgs = False
            for queue_url in queue_urls:
                resp = self.client.receive_message(
                    QueueUrl=queue_url,
                    WaitTimeSeconds=0,
                    MaxNumberOfMessages=self.max_messages,
                )
                msgs = resp.get("Messages", [])

                if not msgs:
                    continue

                has_msgs = True
                for msg in msgs:
                    crash_id = msg["Body"]
                    handle = msg["ReceiptHandle"]
                    logger.debug("got %s from %s", crash_id, queue_url)
                    if crash_id == "test":
                        # Ack and drop any test crash ids
                        self.ack_crash(queue_url, handle)
                        continue
                    yield (
                        (crash_id,),
                        {"finished_func": partial(self.ack_crash, queue_url, handle)},
                    )

            if not has_msgs:
                # There's nothing to process, so return
                return

    def publish(self, queue, crash_ids):
        """Publish crash ids to specified queue.

        :arg queue: the name of the queue to publish to; "standard", "priority" or
            "reprocessing"
        :arg crash_ids: the list of crash ids to publish

        :raises CrashIdsFailedToPublish: raised if there was a failure publishing
            crash ids with the list of crash ids that failed to publish

        """
        assert queue in ["standard", "priority", "reprocessing"]

        failed = []

        queue_url = self.queue_to_queue_url[queue]
        for batch in chunked(crash_ids, 10):
            entry_list = [
                {"Id": str(i), "MessageBody": crash_id}
                for i, crash_id in enumerate(batch)
            ]
            resp = self.client.send_message_batch(
                QueueUrl=queue_url, Entries=entry_list
            )
            for item in resp.get("Failed", []):
                failed.append(entry_list[int(item["Id"])])

        if failed:
            raise CrashIdsFailedToPublish(
                f"Crashids failed to publish: {','.join(failed)}"
            )
