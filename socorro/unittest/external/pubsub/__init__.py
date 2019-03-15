# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import ConfigurationManager
from google.api_core.exceptions import AlreadyExists
from google.cloud import pubsub_v1

from socorro.external.pubsub.crashqueue import PubSubCrashQueue


# Socorro uses three queues. Each is implemented as a Pub/Sub topic and subscription.
QUEUES = ['standard', 'priority', 'reprocessing']

# Pub/Sub acknowledgement deadline in seconds
ACK_DEADLINE = 2


class PubSubHelper:
    """Helper class for setting up, tearing down, and publishing to Pub/Sub."""

    def __init__(self, config):
        # NOTE(willkg): This (lazily) uses the same config as PubSubCrashQueue.
        self.config = config

    def setup_topics(self):
        publisher = pubsub_v1.PublisherClient()
        subscriber = pubsub_v1.SubscriberClient()

        project_id = self.config.project_id

        for queue in QUEUES:
            topic_name = self.config['%s_topic_name' % queue]
            topic_path = publisher.topic_path(project_id, topic_name)

            try:
                publisher.create_topic(topic_path)
            except AlreadyExists:
                pass

            subscription_name = self.config['%s_subscription_name' % queue]
            subscription_path = subscriber.subscription_path(project_id, subscription_name)
            try:
                subscriber.create_subscription(
                    name=subscription_path,
                    topic=topic_path,
                    ack_deadline_seconds=ACK_DEADLINE
                )
            except AlreadyExists:
                pass

    def teardown_topics(self):
        publisher = pubsub_v1.PublisherClient()
        subscriber = pubsub_v1.SubscriberClient()
        project_id = self.config.project_id

        for queue in QUEUES:
            topic_name = self.config['%s_topic_name' % queue]
            topic_path = publisher.topic_path(project_id, topic_name)

            # Delete all subscriptions
            for sub_path in publisher.list_topic_subscriptions(topic_path):
                subscriber.delete_subscription(sub_path)

            # Delete topic
            publisher.delete_topic(topic_path)

    def __enter__(self):
        self.setup_topics()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.teardown_topics()

    def get_crash_ids(self, queue_name):
        subscriber = pubsub_v1.SubscriberClient()
        project_id = self.config.project_id
        sub_name = self.config['%s_subscription_name' % queue_name]
        sub_path = subscriber.subscription_path(project_id, sub_name)

        ack_ids = []
        crash_ids = []
        while True:
            response = subscriber.pull(sub_path, max_messages=1, return_immediately=True)
            if not response.received_messages:
                break

            for msg in response.received_messages:
                crash_ids.append(msg.message.data.decode('utf-8'))
                ack_ids.append(msg.ack_id)

        if ack_ids:
            # Set the ack deadlines to 0 so they go back in the queue
            subscriber.acknowledge(sub_path, ack_ids)

        return crash_ids

    def publish(self, queue_name, crash_id):
        publisher = pubsub_v1.PublisherClient()
        project_id = self.config.project_id

        topic_name = self.config['%s_topic_name' % queue_name]
        topic_path = publisher.topic_path(project_id, topic_name)

        future = publisher.publish(topic_path, data=crash_id.encode('utf-8'))
        future.result()


def get_config_manager():
    pubsub_config = PubSubCrashQueue.get_required_config()
    return ConfigurationManager(
        [pubsub_config],
        app_name='test-pubsub',
        app_description='',
        argv_source=[]
    )
