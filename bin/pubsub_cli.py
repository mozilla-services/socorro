#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Pub/Sub manipulation script.
#
# Note: Run this in the base container which has access to Pub/Sub.
#
# Usage: ./bin/pubsub_cli.py [SUBCOMMAND]

import click
from google.cloud import pubsub_v1
from google.api_core.exceptions import AlreadyExists, NotFound


@click.group()
def pubsub_group():
    """Local dev environment Pub/Sub emulator manipulation script."""


@pubsub_group.command("list_topics")
@click.argument("project_id")
@click.pass_context
def list_topics(ctx, project_id):
    """List topics for this project."""
    click.echo(f"Listing topics in project {project_id}.")
    publisher = pubsub_v1.PublisherClient()

    for topic in publisher.list_topics(project=f"projects/{project_id}"):
        click.echo(topic.name)


@pubsub_group.command("list_subscriptions")
@click.argument("project_id")
@click.argument("topic_name")
@click.pass_context
def list_subscriptions(ctx, project_id, topic_name):
    """List subscriptions for a given topic."""
    click.echo(f"Listing subscriptions in topic {topic_name!r}:")
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    for subscription in publisher.list_topic_subscriptions(topic=topic_path):
        click.echo(subscription)


@pubsub_group.command("create_topic")
@click.argument("project_id")
@click.argument("topic_name")
@click.pass_context
def create_topic(ctx, project_id, topic_name):
    """Create topic."""
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    try:
        publisher.create_topic(name=topic_path)
        click.echo(f"Topic created: {topic_path}")
    except AlreadyExists:
        click.echo("Topic already created.")


@pubsub_group.command("create_subscription")
@click.argument("project_id")
@click.argument("topic_name")
@click.argument("subscription_name")
@click.pass_context
def create_subscription(ctx, project_id, topic_name, subscription_name):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)
    try:
        subscriber.create_subscription(name=subscription_path, topic=topic_path)
        click.echo(f"Subscription created: {subscription_path}")
    except AlreadyExists:
        click.echo("Subscription already created.")


@pubsub_group.command("delete_topic")
@click.argument("project_id")
@click.argument("topic_name")
@click.pass_context
def delete_topic(ctx, project_id, topic_name):
    """Delete a topic."""
    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    # Delete all subscriptions
    for subscription in publisher.list_topic_subscriptions(topic=topic_path):
        click.echo(f"Deleting {subscription} ...")
        subscriber.delete_subscription(subscription=subscription)

    # Delete topic
    try:
        publisher.delete_topic(topic=topic_path)
        click.echo(f"Topic deleted: {topic_name}")
    except NotFound:
        click.echo(f"Topic {topic_name} does not exist.")


@pubsub_group.command("publish")
@click.argument("project_id")
@click.argument("topic_name")
@click.argument("crash_id")
@click.pass_context
def publish(ctx, project_id, topic_name, crash_id):
    """Publish crash_id to a given topic."""
    click.echo(f"Publishing crash_id to topic {topic_name!r}:")
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    future = publisher.publish(topic_path, crash_id.encode("utf-8"), timeout=5)
    click.echo(future.result())


@pubsub_group.command("pull")
@click.argument("project_id")
@click.argument("subscription_name")
@click.option("--ack/--no-ack", is_flag=True, default=False)
@click.option("--max-messages", default=1, type=int)
@click.pass_context
def pull(ctx, project_id, subscription_name, ack, max_messages):
    """Pull crash id from a given subscription."""
    click.echo(f"Pulling crash id from subscription {subscription_name!r}:")
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)

    response = subscriber.pull(
        subscription=subscription_path, max_messages=max_messages
    )
    if not response.received_messages:
        return

    ack_ids = []
    for msg in response.received_messages:
        click.echo(f"crash id: {msg.message.data}")
        ack_ids.append(msg.ack_id)

    if ack:
        # Acknowledges the received messages so they will not be sent again.
        subscriber.acknowledge(subscription=subscription_path, ack_ids=ack_ids)


if __name__ == "__main__":
    pubsub_group()
