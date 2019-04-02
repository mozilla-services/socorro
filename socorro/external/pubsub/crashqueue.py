# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from functools import partial
import logging
import os

from configman import Namespace, RequiredConfig
from google.cloud import pubsub_v1


# Maximum number of messages to pull from a Pub/Sub topic in a single pull
# request
PUBSUB_MAX_MESSAGES = 5


logger = logging.getLogger(__name__)


class PubSubCrashQueue(RequiredConfig):
    """Crash queue that uses Pub/Sub.

    This requires three Pub/Sub topics:

    * **standard topic**: processing incoming crashes from the collector
    * **priority topic**: processing crashes right now because someone/something
      is trying to view them
    * **reprocessing topic**: reprocessing crashes after a change to the processor
      that have (probably) already been processed

    Each of those topics requires a subscription.

    Further, this requires a service credentials file for a service account
    that has subscriber permissions to those three subscriptions.

    """

    required_config = Namespace()
    required_config.add_option(
        'service_account_file',
        doc='The absolute path to the JSON service account credentials file.',
        reference_value_from='resource.pubsub'
    )
    required_config.add_option(
        'project_id',
        doc='The Google Compute Platform project_id.',
        reference_value_from='resource.pubsub'
    )
    required_config.add_option(
        'standard_topic_name',
        doc='The topic name for the standard queue.',
        reference_value_from='resource.pubsub'
    )
    required_config.add_option(
        'standard_subscription_name',
        doc='The subscription name for the standard queue.',
        reference_value_from='resource.pubsub'
    )
    required_config.add_option(
        'priority_topic_name',
        doc='The topic name for the priority queue.',
        reference_value_from='resource.pubsub'
    )
    required_config.add_option(
        'priority_subscription_name',
        doc='The subscription name for the priority queue.',
        reference_value_from='resource.pubsub'
    )
    required_config.add_option(
        'reprocessing_topic_name',
        doc='The topic name for the reprocessing queue.',
        reference_value_from='resource.pubsub'
    )
    required_config.add_option(
        'reprocessing_subscription_name',
        doc='The subscription name for the reprocessing queue.',
        reference_value_from='resource.pubsub'
    )

    def __init__(self, config, namespace='', quit_check_callback=None):
        self.config = config
        self.quit_check_callback = quit_check_callback

        if os.environ.get('PUBSUB_EMULATOR_HOST', ''):
            self.subscriber = pubsub_v1.SubscriberClient()
        else:
            self.subscriber = pubsub_v1.SubscriberClient.from_service_account_file(
                self.config.service_account_file
            )
        self.standard_path = self.subscriber.subscription_path(
            self.config.project_id, self.config.standard_subscription_name
        )
        self.priority_path = self.subscriber.subscription_path(
            self.config.project_id, self.config.priority_subscription_name
        )
        self.reprocessing_path = self.subscriber.subscription_path(
            self.config.project_id, self.config.reprocessing_subscription_name
        )

        # NOTE(willkg): This will fail if one of the subscription names don't
        # exist
        self.subscriber.get_subscription(self.standard_path)
        self.subscriber.get_subscription(self.priority_path)
        self.subscriber.get_subscription(self.reprocessing_path)

    def ack_crash(self, sub_path, ack_id):
        self.subscriber.acknowledge(sub_path, [ack_id])
        logger.debug('ack %s from %s', ack_id, sub_path)

    def close(self):
        pass

    def __iter__(self):
        """Return iterator over crash ids from Pub/Sub.

        Each returned crash is a ``(crash_id, {kwargs})`` tuple with
        ``finished_func`` as the only key in ``kwargs``. The caller should call
        ``finished_func`` when it's done processing the crash.

        """
        sub_paths = [
            self.priority_path,
            self.standard_path,
            self.reprocessing_path,
        ]

        while True:
            msgs = 0
            for sub_path in sub_paths:
                response = self.subscriber.pull(
                    sub_path,
                    max_messages=PUBSUB_MAX_MESSAGES,
                    return_immediately=True
                )
                if response.received_messages:
                    msgs += 1
                    for msg in response.received_messages:
                        crash_id = msg.message.data.decode('utf-8')
                        logger.debug('got %s from %s', crash_id, sub_path)
                        if crash_id == 'test':
                            # Ack and drop any test crash ids
                            self.ack_crash(sub_path, msg.ack_id)
                            continue
                        yield (
                            (crash_id,),
                            {'finished_func': partial(self.ack_crash, sub_path, msg.ack_id)}
                        )
            if msgs == 0:
                # There's nothing to process, so return
                return

    def new_crashes(self):
        return self.__iter__()

    def __call__(self):
        return self.__iter__()

    def publish(self, queue, crash_ids):
        """Publish crash ids to specified queue."""
        assert queue in ['standard', 'priority', 'reprocessing']

        if os.environ.get('PUBSUB_EMULATOR_HOST', ''):
            publisher = pubsub_v1.PublisherClient()
        else:
            publisher = pubsub_v1.PublisherClient.from_service_account_file(
                self.config.service_account_file
            )
        project_id = self.config.project_id
        topic_name = self.config['%s_topic_name' % queue]
        topic_path = publisher.topic_path(project_id, topic_name)

        # Queue up the batch
        futures = []
        for crash_id in crash_ids:
            futures.append(publisher.publish(topic_path, data=crash_id.encode('utf-8')))

        # Wait for everything in this group to get sent out
        for future in futures:
            future.result()
