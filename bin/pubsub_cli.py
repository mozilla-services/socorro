#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Pub/Sub manipulation script.
#
# Note: Run this in the base container which has access to Pub/Sub.
#
# Usage: ./bin/pubsub_cli.py [SUBCOMMAND]

import sys

import click
from google.cloud import pubsub_v1
from google.api_core.exceptions import AlreadyExists, NotFound

from socorro import settings


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
    """Create subscription."""
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)
    try:
        subscriber.create_subscription(
            name=subscription_path,
            topic=topic_path,
            ack_deadline_seconds=600,
        )
        click.echo(f"Subscription created: {subscription_path}")
    except AlreadyExists:
        click.echo("Subscription already created.")


@pubsub_group.command("delete_topic")
@click.argument("project_id")
@click.argument("topic_name")
@click.pass_context
def delete_topic(ctx, project_id, topic_name):
    """Delete a topic and all subscriptions."""
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
@click.argument("crashids", nargs=-1)
@click.pass_context
def publish(ctx, project_id, topic_name, crashids):
    """Publish crash_id to a given topic."""
    click.echo(f"Publishing crash ids to topic: {topic_name!r}:")
    # configure publisher to group all crashids into a single batch
    publisher = pubsub_v1.PublisherClient(
        batch_settings=pubsub_v1.types.BatchSettings(max_messages=len(crashids))
    )
    topic_path = publisher.topic_path(project_id, topic_name)

    # Pull crash ids from stdin if there are any
    if not crashids and not sys.stdin.isatty():
        crashids = list(click.get_text_stream("stdin").readlines())

    if not crashids:
        raise click.BadParameter(
            "No crashids provided.", ctx=ctx, param="crashids", param_hint="crashids"
        )

    # publish all crashes before checking futures to allow for batching
    futures = [
        publisher.publish(topic_path, crashid.encode("utf-8"), timeout=5)
        for crashid in crashids
    ]
    for future in futures:
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
        subscription=subscription_path,
        max_messages=max_messages,
        return_immediately=True,
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


@pubsub_group.command("create-all")
@click.pass_context
def create_all(ctx):
    """Create Pub/Sub queues related to processing."""
    options = settings.QUEUE_PUBSUB["options"]
    project_id = options["project_id"]
    queues = {
        options["standard_topic_name"]: options["standard_subscription_name"],
        options["priority_topic_name"]: options["priority_subscription_name"],
        options["reprocessing_topic_name"]: options["reprocessing_subscription_name"],
    }
    for topic_name, subscription_name in queues.items():
        ctx.invoke(create_topic, project_id=project_id, topic_name=topic_name)
        ctx.invoke(
            create_subscription,
            project_id=project_id,
            topic_name=topic_name,
            subscription_name=subscription_name,
        )


@pubsub_group.command("delete-all")
@click.pass_context
def delete_all(ctx):
    """Delete Pub/Sub queues related to processing."""
    options = settings.QUEUE_PUBSUB["options"]
    project_id = options["project_id"]
    for topic_name in (
        options["standard_topic_name"],
        options["priority_topic_name"],
        options["reprocessing_topic_name"],
    ):
        ctx.invoke(delete_topic, project_id=project_id, topic_name=topic_name)


def main(argv=None):
    argv = argv or []
    pubsub_group(argv)


if __name__ == "__main__":
    pubsub_group()
