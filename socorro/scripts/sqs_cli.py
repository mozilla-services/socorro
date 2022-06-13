#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# SQS manipulation script.
#
# Note: Run this in the base container which has access to SQS.
#
# Usage: socorro-cmd sqs [SUBCOMMAND]

import os
import sys
import time

import boto3
import click


VISIBILITY_TIMEOUT = 2


class InvalidQueueName(Exception):
    """Denotes an invalid queue name."""


def validate_queue_name(queue_name):
    if len(queue_name) > 80:
        raise InvalidQueueName("queue name is too long.")

    for c in queue_name:
        if not c.isalnum() and c not in "-_":
            raise InvalidQueueName("%r is not an alphanumeric, - or _ character." % c)


def get_client():
    session = boto3.session.Session(
        aws_access_key_id=os.environ.get("resource.boto.access_key"),
        aws_secret_access_key=os.environ.get("secrets.boto.secret_access_key"),
    )
    client = session.client(
        service_name="sqs",
        region_name=os.environ.get("resource.boto.region"),
        endpoint_url=os.environ.get("resource.boto.sqs_endpoint_url"),
    )
    return client


@click.group()
def sqs_group():
    """Local dev environment SQS manipulation script."""


@sqs_group.command("list_messages")
@click.argument("queue")
@click.pass_context
def list_messages(ctx, queue):
    """List messages in queue."""
    conn = get_client()
    try:
        resp = conn.get_queue_url(QueueName=queue)
        queue_url = resp["QueueUrl"]
    except conn.exceptions.QueueDoesNotExist:
        click.echo("Queue %s does not exist.")
        return

    # NOTE(willkg): Since the VisibilityTimeout is set to VISIBILITY_TIMEOUT and
    # messages aren't deleted, items aren't pulled out of the queue permanently.
    # However, if you run list_messages twice in rapid succession, VisibilityTimeout may
    # not have passed, so we wait the timeout amount first.
    time.sleep(VISIBILITY_TIMEOUT)

    is_empty = True
    while True:
        resp = conn.receive_message(
            QueueUrl=queue_url,
            WaitTimeSeconds=0,
            VisibilityTimeout=VISIBILITY_TIMEOUT,
        )
        msgs = resp.get("Messages", [])
        if not msgs:
            break

        is_empty = False
        for msg in msgs:
            click.echo("%s" % msg["Body"])

    if is_empty:
        click.echo("Queue %s is empty." % queue)


@sqs_group.command("publish")
@click.argument("queue")
@click.argument("crashids", nargs=-1)
@click.pass_context
def publish(ctx, queue, crashids):
    """Publishes crash ids to a queue."""
    conn = get_client()
    try:
        resp = conn.get_queue_url(QueueName=queue)
        queue_url = resp["QueueUrl"]
    except conn.exceptions.QueueDoesNotExist:
        click.echo("Queue %s does not exist.")
        return

    # Pull crash ids from stdin if there are any
    if not crashids and not sys.stdin.isatty():
        crashids = list(click.get_text_stream("stdin").readlines())

    if not crashids:
        raise click.BadParameter(
            "No crashids provided.", ctx=ctx, param="crashids", param_hint="crashids"
        )

    for crashid in crashids:
        crashid = crashid.rstrip()
        conn.send_message(QueueUrl=queue_url, MessageBody=crashid)
        click.echo("Published: %s" % crashid)


@sqs_group.command("list_queues")
@click.pass_context
def list_queues(ctx):
    """List queues."""
    conn = get_client()
    resp = conn.list_queues()

    for queue_url in resp.get("QueueUrls", []):
        queue_name = queue_url.rsplit("/", 1)[1]
        click.echo(queue_name)


@sqs_group.command("create")
@click.argument("queue")
@click.pass_context
def create(ctx, queue):
    """Create SQS queue."""
    queue = queue.strip()
    if not queue:
        click.echo("Queue name required.")
        return

    conn = get_client()
    validate_queue_name(queue)
    try:
        conn.get_queue_url(QueueName=queue)
        click.echo("Queue %s already exists." % queue)
        return
    except conn.exceptions.QueueDoesNotExist:
        pass
    conn.create_queue(QueueName=queue)
    click.echo("Queue %s created." % queue)


@sqs_group.command("create-all")
@click.pass_context
def create_all(ctx):
    """Create SQS queues related to processing."""
    ctx.invoke(create, queue=os.environ["resource.boto.standard_queue"])
    ctx.invoke(create, queue=os.environ["resource.boto.priority_queue"])
    ctx.invoke(create, queue=os.environ["resource.boto.reprocessing_queue"])


@sqs_group.command("delete")
@click.argument("queue")
@click.pass_context
def delete(ctx, queue):
    """Delete SQS queue."""
    queue = queue.strip()
    if not queue:
        click.echo("Queue name required.")
        return

    conn = get_client()
    try:
        resp = conn.get_queue_url(QueueName=queue)
    except conn.exceptions.QueueDoesNotExist:
        click.echo("Queue %s does not exist." % queue)
        return

    queue_url = resp["QueueUrl"]
    conn.delete_queue(QueueUrl=queue_url)
    click.echo("Queue %s deleted." % queue)


@sqs_group.command("delete-all")
@click.pass_context
def delete_all(ctx):
    """Delete SQS queues related to processing."""
    ctx.invoke(delete, queue=os.environ["resource.boto.standard_queue"])
    ctx.invoke(delete, queue=os.environ["resource.boto.priority_queue"])
    ctx.invoke(delete, queue=os.environ["resource.boto.reprocessing_queue"])


def main(argv=None):
    argv = argv or []
    sqs_group(argv)


if __name__ == "__main__":
    sqs_group()
