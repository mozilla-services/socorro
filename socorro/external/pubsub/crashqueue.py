# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from functools import partial
import logging
import os

from configman import Namespace, RequiredConfig
from google.cloud import pubsub_v1


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

        if 'PUBSUB_EMULATOR_HOST' in os.environ:
            self.subscriber = pubsub_v1.SubscriberClient()
        else:
            self.subscriber = pubsub_v1.SubscriberClient.from_service_account_file(
                config.service_account_file
            )
        self.standard_path = self.subscriber.subscription_path(
            config.project_id, config.standard_subscription_name
        )
        self.priority_path = self.subscriber.subscription_path(
            config.project_id, config.priority_subscription_name
        )
        self.reprocessing_path = self.subscriber.subscription_path(
            config.project_id, config.reprocessing_subscription_name
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

        This does a single pass through the queues and pulls at most 10 from
        each queue. It tries twice to pull from the priority queue since it's
        a priority queue.

        """
        queues = [
            self.priority_path,
            self.standard_path,
            self.reprocessing_path,
            self.priority_path
        ]

        for queue_path in queues:
            response = self.subscriber.pull(
                queue_path,
                max_messages=1,
                return_immediately=True
            )
            if response.received_messages:
                for msg in response.received_messages:
                    crash_id = msg.message.data.decode('utf-8')
                    logger.debug('got %s from %s', crash_id, queue_path)
                    if crash_id == 'test':
                        # Drop any test crash ids
                        continue
                    yield (
                        (crash_id,),
                        {'finished_func': partial(self.ack_crash, queue_path, msg.ack_id)}
                    )

    def new_crashes(self):
        return self.__iter__()

    def __call__(self):
        return self.__iter__()

    def publish(self, queue, crash_ids):
        """Publish crash ids to specified queue."""
        assert queue in ['standard', 'priority', 'reprocessing']

        publisher = pubsub_v1.PublisherClient()
        project_id = self.config.project_id
        topic_name = self.config['%s_topic_name' % queue]
        topic_path = publisher.topic_path(project_id, topic_name)

        for crash_id in crash_ids:
            future = publisher.publish(topic_path, data=crash_id.encode('utf-8'))
            future.result()
