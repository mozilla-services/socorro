# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from functools import partial
import logging
import os

from google.cloud.pubsub_v1 import PublisherClient, SubscriberClient
from google.cloud.pubsub_v1.types import BatchSettings, PublisherOptions
from more_itertools import chunked

from socorro.external.crashqueue_base import CrashQueueBase


logger = logging.getLogger(__name__)


class CrashIdsFailedToPublish(Exception):
    """Crash ids that failed to publish."""


class PubSubCrashQueue(CrashQueueBase):
    """Crash queue that uses Google Cloud Pub/Sub.

    This requires three Google Cloud Pub/Sub topics with subscriptions:

    * **standard**: processing incoming crashes from the collector
    * **priority**: processing crashes right now because someone/something
      is trying to view them
    * **reprocessing**: reprocessing crashes after a change to the processor
      that have (probably) already been processed

    and they need the following settings:

    ==========================  =========
    Setting                     Value
    ==========================  =========
    Acknowledgement deadline    5 minutes
    Message retention duration  *default*
    ==========================  =========

    The GCP credentials that Socorro is configured with must have the following
    permissions on the Pub/Sub topics and subscriptions configured:

    * ``roles/pubsub.publisher``

      Socorro webapp sends messages to topics--this is how the webapp publishes crash
      ids to the priority and reprocessing queues. This requires permissions from the
      ``roles/pubsub.publisher`` role.

    * ``roles/pubsub.subscriber``

      The Socorro processor has to receive messages from the configured subscriptions
      in order to process the related crash reports. This requires permissions from the
      ``roles/pubsub.subscriber`` role.

    If something isn't configured correctly, then the Socorro processor will be unable
    to process crashes and the webapp will be unable to publish crash ids for
    processing.


    **Authentication**

    The google cloud sdk will automatically detect credentials as described in
    https://googleapis.dev/python/google-api-core/latest/auth.html:

    - If you're running in a Google Virtual Machine Environment (Compute Engine, App
      Engine, Cloud Run, Cloud Functions), authentication should "just work".

    - If you're developing locally, the easiest way to authenticate is using the `Google
      Cloud SDK <http://cloud.google.com/sdk>`_::

        $ gcloud auth application-default login

    - If you're running your application elsewhere, you should download a `service account
      <https://cloud.google.com/iam/docs/creating-managing-service-accounts#creating>`_
      JSON keyfile and point to it using an environment variable::

        $ export GOOGLE_APPLICATION_CREDENTIALS="/path/to/keyfile.json"


    **Local emulator**

    If you set the environment variable ``PUBSUB_EMULATOR_HOST=host:port``,
    then this will connect to a local Pub/Sub emulator.

    """

    def __init__(
        self,
        project_id,
        standard_topic_name,
        standard_subscription_name,
        priority_topic_name,
        priority_subscription_name,
        reprocessing_topic_name,
        reprocessing_subscription_name,
        pull_max_messages=5,
        publish_max_messages=10,
        publish_timeout=5,
    ):
        """
        :arg project_id: Google Compute Platform project_id
        :arg standard_topic_name: topic name for the standard queue
        :arg standard_subscription_name: subscription name for the standard queue
        :arg priority_topic_name: topic name for the priority processing queue
        :arg priority_subscription_name: subscription name for the priority queue
        :arg reprocessing_topic_name: topic name for the reprocessing queue
        :arg reprocessing_subscription_name: subscription name for the reprocessing
            queue
        :arg pull_max_messages: maximum number of messages to pull from Google Pub/Sub
            in a single request
        :arg publish_max_messages: maximum number of messages to publish to Google
            Pub/Sub in a single request
        :arg publish_timeout: rpc timeout for publish requests
        """

        if emulator := os.environ.get("PUBSUB_EMULATOR_HOST"):
            logger.debug(
                "PUBSUB_EMULATOR_HOST detected, connecting to emulator: %s",
                emulator,
            )
        self.publisher = PublisherClient(
            # publish messages in batches
            batch_settings=BatchSettings(max_messages=publish_max_messages),
            # disable retry in favor of socorro's retry and set rpc timeout
            publisher_options=PublisherOptions(retry=None, timeout=publish_timeout),
        )

        def create_topic_path(publisher, project_id, name):
            return publisher.topic_path(project_id, name) if name else None

        self.standard_topic_path = create_topic_path(
            self.publisher, project_id, standard_topic_name
        )
        self.priority_topic_path = create_topic_path(
            self.publisher, project_id, priority_topic_name
        )
        self.reprocessing_topic_path = create_topic_path(
            self.publisher, project_id, reprocessing_topic_name
        )

        self.queue_to_topic_path = {
            "standard": self.standard_topic_path,
            "priority": self.priority_topic_path,
            "reprocessing": self.reprocessing_topic_path,
        }

        self.subscriber = SubscriberClient()

        def create_subscription_path(subscriber, project_id, name):
            return subscriber.subscription_path(project_id, name) if name else None

        self.standard_subscription_path = create_subscription_path(
            self.subscriber, project_id, standard_subscription_name
        )
        self.priority_subscription_path = create_subscription_path(
            self.subscriber, project_id, priority_subscription_name
        )
        self.reprocessing_subscription_path = create_subscription_path(
            self.subscriber, project_id, reprocessing_subscription_name
        )

        # Order matters here, and is checked in tests
        self.queue_to_subscription_path = {
            "standard": self.standard_subscription_path,
            "priority": self.priority_subscription_path,
            "reprocessing": self.reprocessing_subscription_path,
        }

        self.pull_max_messages = pull_max_messages
        self.publish_max_messages = publish_max_messages

    def ack_crash(self, subscription_path, ack_id):
        """Acknowledges a crash

        :arg subscription_path: the subscription path for the queue
        :arg ack_id: the ack_id for the message to acknowledge

        """
        self.subscriber.acknowledge(subscription=subscription_path, ack_ids=[ack_id])
        logger.debug("ack %s from %s", ack_id, subscription_path)

    def __iter__(self):
        """Return iterator over crash ids from Pub/Sub.

        Each returned crash is a ``(crash_id, {kwargs})`` tuple with
        ``finished_func`` as the only key in ``kwargs``. The caller should call
        ``finished_func`` when it's done processing the crash.

        """
        while True:
            has_msgs = {}
            for subscription_path in self.queue_to_subscription_path.values():
                if subscription_path is None:
                    continue

                resp = self.subscriber.pull(
                    subscription=subscription_path,
                    max_messages=self.pull_max_messages,
                    return_immediately=True,
                )
                msgs = resp.received_messages

                # if pull returned the max number of messages, this subscription
                # may have more messages.
                has_msgs[subscription_path] = len(msgs) == self.pull_max_messages

                if not msgs:
                    continue

                for msg in msgs:
                    crash_id = msg.message.data.decode("utf-8")
                    ack_id = msg.ack_id
                    logger.debug("got %s from %s", crash_id, subscription_path)
                    if crash_id == "test":
                        # Ack and drop any test crash ids
                        self.ack_crash(subscription_path, ack_id)
                        continue
                    yield (
                        (crash_id,),
                        {
                            "finished_func": partial(
                                self.ack_crash, subscription_path, ack_id
                            )
                        },
                    )

            if not any(has_msgs.values()):
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
        topic_path = self.queue_to_topic_path.get(queue)
        if topic_path is None:
            logger.warning(
                "asked to publish to topic %s which has None topic path",
                queue,
            )
            return

        failed = []

        for batch in chunked(crash_ids, self.publish_max_messages):
            futures = [
                self.publisher.publish(topic=topic_path, data=crash_id.encode("utf-8"))
                for crash_id in batch
            ]
            for i, future in enumerate(futures):
                try:
                    future.result()
                except Exception:
                    logger.exception(
                        "Crashid failed to publish: %s %s",
                        queue,
                        batch[i],
                    )
                    failed.append(batch[i])

        if failed:
            raise CrashIdsFailedToPublish(
                f"Crashids failed to publish: {','.join(failed)}"
            )
