# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from functools import partial
import logging
import random
import time

import boto3
from botocore.client import ClientError
from configman import Namespace
from more_itertools import chunked

from socorro.external.crashqueue_base import CrashQueueBase
from socorro.lib.util import retry


# Maximum number of messages to pull from an SQS queue in a single pull request
SQS_MAX_MESSAGES = 5


logger = logging.getLogger(__name__)


class CrashIdsFailedToPublish(Exception):
    """Crash ids that failed to publish."""


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
      process the related crash reports. This requires teh ``sqs:ReceiveMessage``
      permission.

    If something isn't configured correctly, then the Socorro processor will be unable
    to process crashes and the webapp will be unable to publish crash ids for
    processing.

    """

    required_config = Namespace()
    required_config.add_option(
        "access_key",
        doc="access key",
        reference_value_from="resource.boto",
    )
    required_config.add_option(
        "secret_access_key",
        doc="secret access key",
        secret=True,
        reference_value_from="secrets.boto",
    )
    required_config.add_option(
        "region",
        doc="Name of the S3 region (e.g. us-west-2)",
        default="us-west-2",
        reference_value_from="resource.boto",
    )
    required_config.add_option(
        "sqs_endpoint_url",
        doc=(
            "endpoint url to connect to; None if you are connecting to AWS. For "
            "example, ``http://localhost:4572/``."
        ),
        default="",
        reference_value_from="resource.boto",
    )
    required_config.add_option(
        "standard_queue",
        doc="The name for the standard queue.",
        reference_value_from="resource.boto",
    )
    required_config.add_option(
        "priority_queue",
        doc="The name for the priority queue.",
        reference_value_from="resource.boto",
    )
    required_config.add_option(
        "reprocessing_queue",
        doc="The name for the reprocessing queue.",
        reference_value_from="resource.boto",
    )

    def __init__(self, config, namespace=""):
        super().__init__(config, namespace)

        self.client = self.build_client()
        self.standard_queue_url = self.get_queue_url(self.config.standard_queue)
        self.priority_queue_url = self.get_queue_url(self.config.priority_queue)
        self.reprocessing_queue_url = self.get_queue_url(self.config.reprocessing_queue)
        self.queue_to_queue_url = {
            "standard": self.standard_queue_url,
            "priority": self.priority_queue_url,
            "reprocessing": self.reprocessing_queue_url,
        }

    def get_queue_url(self, queue_name):
        return self.client.get_queue_url(QueueName=queue_name)["QueueUrl"]

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
        """Returns a Boto3 SQS Client."""
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
            "service_name": "sqs",
            "region_name": self.config.region,
        }
        if self.config.sqs_endpoint_url:
            kwargs["endpoint_url"] = self.config.sqs_endpoint_url

        return session.client(**kwargs)

    def ack_crash(self, queue_url, handle):
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
                    MaxNumberOfMessages=SQS_MAX_MESSAGES,
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
        """Publish crash ids to specified queue."""
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
                "Crashids failed to publish: %s", ",".join(failed)
            )
