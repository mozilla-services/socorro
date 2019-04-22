# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Pub/Sub manipulation script.

import argparse
import os
import sys

from google.api_core.exceptions import AlreadyExists, NotFound
from google.cloud import pubsub_v1

from socorro.scripts import FallbackToPipeAction, WrappedTextHelpFormatter


DESCRIPTION = 'Local dev environment Pub/Sub emulator manipulation script.'

ENV_VARS = [
    'resource.pubsub.project_id',
    'resource.pubsub.standard_topic_name',
    'resource.pubsub.standard_subscription_name',
    'resource.pubsub.priority_topic_name',
    'resource.pubsub.priority_subscription_name',
    'resource.pubsub.reprocessing_topic_name',
    'resource.pubsub.reprocessing_subscription_name'
]

EPILOG = 'Requires %s, and %s to be set in the environment.' % (
    ', '.join(ENV_VARS[:-1]), ENV_VARS[-1]
)

# Number of seconds Pub/Sub should wait for a message to be acknowledged
ACK_DEADLINE = 120


def get_crash_ids(sub_path):
    """Fetch everything from queue and reset queue."""
    subscriber = pubsub_v1.SubscriberClient()

    # NOTE(willkg): The Pub/Sub emulator doesn't support snapshots or seek so
    # we keep the ack ids and then modify the ack deadline to 0 which puts them
    # back in the queue

    ack_ids = []
    crash_ids = []
    while True:
        response = subscriber.pull(sub_path, max_messages=1, return_immediately=True)
        if not response.received_messages:
            break

        for msg in response.received_messages:
            crash_ids.append(msg.message.data)
            ack_ids.append(msg.ack_id)

    if ack_ids:
        # Set the ack deadlines to 0 so they go back in the queue
        subscriber.modify_ack_deadline(sub_path, ack_ids, 0)

    return crash_ids


def create_topics(config, args):
    """Create topics and subscriptions."""
    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()

    project_id = config['resource.pubsub.project_id']

    for queue in ['standard', 'priority', 'reprocessing']:
        topic_name = config['resource.pubsub.%s_topic_name' % queue]
        topic_path = publisher.topic_path(project_id, topic_name)

        try:
            publisher.create_topic(topic_path)
            print('Topic created: %s' % topic_path)
        except AlreadyExists:
            print('Topic %s already created.' % topic_path)

        subscription_name = config['resource.pubsub.%s_subscription_name' % queue]
        subscription_path = subscriber.subscription_path(project_id, subscription_name)
        try:
            subscriber.create_subscription(
                name=subscription_path,
                topic=topic_path,
                ack_deadline_seconds=ACK_DEADLINE
            )
            print('Subscription created: %s' % subscription_path)
        except AlreadyExists:
            print('Subscription %s already created.' % subscription_path)


def delete_topics(config, args):
    """Delete topics and subscriptions."""
    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()
    project_id = config['resource.pubsub.project_id']

    for queue in ['standard', 'priority', 'reprocessing']:
        topic_name = config['resource.pubsub.%s_topic_name' % queue]
        topic_path = publisher.topic_path(project_id, topic_name)

        # Delete all subscriptions
        for subscription in publisher.list_topic_subscriptions(topic_path):
            subscriber.delete_subscription(subscription)
            print('Subscription deleted: %s' % subscription)

        # Delete topic
        try:
            publisher.delete_topic(topic_path)
            print('Topic deleted: %s' % topic_name)
        except NotFound:
            pass


def status(config, args):
    """Shows status of Pub/Sub emulator."""
    publisher = pubsub_v1.PublisherClient()

    project_id = config['resource.pubsub.project_id']
    project_path = publisher.project_path(project_id)

    print('Project id: %s' % project_id)
    for topic in publisher.list_topics(project_path):
        topic_path = topic.name
        print('   topic: %s' % topic_path)

        for sub_path in publisher.list_topic_subscriptions(topic_path):
            print('      subscription: %s' % sub_path)

            crash_ids = get_crash_ids(sub_path)
            print('         crashids: %s' % len(crash_ids))
            for crash_id in crash_ids:
                print('             %s' % crash_id)


def publish_crashid(config, queue, crashids):
    publisher = pubsub_v1.PublisherClient()
    project_id = config['resource.pubsub.project_id']

    topic_name = config['resource.pubsub.%s_topic_name' % queue]
    topic_path = publisher.topic_path(project_id, topic_name)

    for crash_id in crashids:
        future = publisher.publish(topic_path, data=crash_id.encode('utf-8'))
        future.result()
        print('Published: %s' % crash_id)


def main(argv=None):
    if not os.environ.get('PUBSUB_EMULATOR_HOST', ''):
        print('WARNING: You are running against the real GCP and not the emulator.')
        print('This does not work with the real GCP.')
        sys.exit(1)

    parser = argparse.ArgumentParser(
        formatter_class=WrappedTextHelpFormatter,
        description=DESCRIPTION.strip(),
        epilog=EPILOG.strip()
    )
    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.required = True
    subparsers.add_parser('create', help='Create topics and subscriptions.')
    subparsers.add_parser('delete', help='Delete topics and subscriptions.')
    subparsers.add_parser('status', help='Show status of everything.')
    publish_parser = subparsers.add_parser('publish', help='Publish a crash id to a topic.')
    publish_parser.add_argument('--queue', default='standard', help='Queue to publish to.')
    publish_parser.add_argument('crashid', help='Crash id(s) to publish.',
                                nargs='*', action=FallbackToPipeAction)

    args, remaining = parser.parse_known_args()

    config = {}
    for env_var in ENV_VARS:
        try:
            config[env_var] = os.environ[env_var]
        except KeyError:
            parser.error('%s is not set in environment.' % env_var)

    if args.cmd == 'create':
        return create_topics(config, args)
    elif args.cmd == 'delete':
        return delete_topics(config, args)
    elif args.cmd == 'status':
        return status(config, args)
    elif args.cmd == 'publish':
        return publish_crashid(config, args.queue, args.crashid)
