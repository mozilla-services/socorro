# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import time

from configman import ConfigurationManager
from google.api_core.exceptions import AlreadyExists
from google.cloud import pubsub_v1

from socorro.external.pubsub.crashqueue import PubSubCrashQueue
from socorro.lib.ooid import create_new_ooid


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


class TestPubSubCrashQueue:
    def test_iter(self):
        manager = get_config_manager()
        with manager.context() as config:
            pubsub_helper = PubSubHelper(config)

            with pubsub_helper as pubsub:
                standard_crash = create_new_ooid()
                pubsub.publish('standard', standard_crash)

                reprocessing_crash = create_new_ooid()
                pubsub.publish('reprocessing', reprocessing_crash)

                priority_crash = create_new_ooid()
                pubsub.publish('priority', priority_crash)

                crash_queue = PubSubCrashQueue(config)
                new_crashes = list(crash_queue.new_crashes())

        # Assert the shape of items in new_crashes
        for item in new_crashes:
            assert isinstance(item, tuple)
            assert isinstance(item[0], tuple)  # *args
            assert isinstance(item[1], dict)   # **kwargs
            assert list(item[1].keys()) == ['finished_func']

        # Assert new_crashes order is the correct order
        crash_ids = [item[0][0] for item in new_crashes]
        assert crash_ids == [priority_crash, standard_crash, reprocessing_crash]

    def test_ack(self):
        original_crash_id = create_new_ooid()

        manager = get_config_manager()
        with manager.context() as config:
            pubsub_helper = PubSubHelper(config)

            with pubsub_helper as pubsub:
                # Publish crash id to the queue
                pubsub.publish('standard', original_crash_id)

                crash_queue = PubSubCrashQueue(config)
                new_crashes = list(crash_queue.new_crashes())

                # Assert original_crash_id is in new_crashes
                crash_ids = [item[0][0] for item in new_crashes]
                assert crash_ids == [original_crash_id]

                # Now call it again; note that we haven't acked the crash_ids
                # nor have the leases expired
                second_new_crashes = list(crash_queue.new_crashes())
                assert second_new_crashes == []

                # Now ack the crash_id and we don't get it again
                for args, kwargs in new_crashes:
                    kwargs['finished_func']()

                # Wait beyond the ack deadline in the grossest way possible
                time.sleep(ACK_DEADLINE + 1)

                # Now call it again and make sure we get nothing back
                new_crashes = list(crash_queue.new_crashes())
                assert new_crashes == []
