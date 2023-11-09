#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Given a set of crash reports ids via a file, removes all crash report data from
all crash storage:

* S3

  * raw crash
  * dump_names
  * minidump files
  * processed crash

* Elasticsearch

  * crash report document

Notes:

1. This **deletes** crash data permanently. Once deleted, this data can't be undeleted.
2. This doesn't delete any data from cache. Caches will expire data eventually.

Usage::

    python bin/permadelete_crash_data.py CRASHIDSFILE

"""

import json
import logging
import os

import click
from elasticsearch_dsl import Search

from socorro import settings
from socorro.external.boto.crashstorage import build_keys
from socorro.libclass import build_instance_from_settings


logging.basicConfig()

logger = logging.getLogger(__name__)


def crashid_generator(fn):
    """Lazily yield crash ids."""
    with open(fn) as fp:
        for line in fp:
            line = line.strip()
            if line.startswith("#"):
                continue
            yield line


def get_s3_crashstorage():
    """Return an S3ConnectionContext."""
    return build_instance_from_settings(settings.CRASH_DESTINATIONS["s3"])


def s3_delete_object(client, bucket, key):
    """Deletes a specific object from S3.

    Requires s3:DeleteObject.

    :arg client: the s3 client
    :arg bucket: the bucket name
    :arg key: the key of the object to delete

    :return: True if the delete was fine or already not there; False if there was an
        error

    """
    try:
        client.delete_object(Bucket=bucket, Key=key)
        click.echo(f"s3: deleted {key!r}")
        return True
    except Exception:
        logger.exception("ERROR: s3: when deleting %r", key)
        return False


def s3_fetch_object(client, bucket, key):
    """Fetch an object from S3 with appropriate handling for issues.

    Requires s3:GetObject.

    :arg client: the s3 client
    :arg bucket: the bucket name
    :arg key: the key of the object to delete

    :returns: Body or None

    """
    try:
        resp = client.get_object(Bucket=bucket, Key=key)
        return resp["Body"].read()
    except client.exceptions.NoSuchKey:
        click.echo(f"s3: not found: {key!r}")
    except Exception:
        logger.exception("ERROR: s3: when fetching %r", key)


def s3_delete(crashid):
    """Delete crash report data from S3."""
    s3_crashstorage = get_s3_crashstorage()
    bucket = s3_crashstorage.bucket
    s3_client = s3_crashstorage.connection.client

    keys = build_keys("raw_crash", crashid)
    for key in keys:
        obj = s3_fetch_object(s3_client, bucket, key)
        if obj:
            s3_delete_object(s3_client, bucket, key)

    # Fetch dump_names which tells us which dumps exist
    keys = build_keys("dump_names", crashid)
    dump_names = []
    for key in keys:
        data = s3_fetch_object(s3_client, bucket, key)
        if data:
            try:
                # dump_names is a JSON encoded list of strings
                dump_names.extend(json.loads(data))
            except Exception:
                logger.exception(
                    "ERROR: %s: s3: when parsing dump_names json" % crashid
                )

    if dump_names:
        # For each dump, delete it if it exists
        dump_errors = 0

        for dump_name in dump_names:
            # Handle dump_name -> key goofiness
            if dump_name in (None, "", "upload_file_minidump"):
                dump_name = "dump"

            keys = build_keys(dump_name, crashid)
            for key in keys:
                # If the dump is not there, that's fine; but if deleting the dump kicks
                # up an error, we want to make sure we don't delete dump_names.
                obj = s3_fetch_object(s3_client, bucket, key)
                if obj:
                    if not s3_delete_object(s3_client, bucket, key):
                        dump_errors += 1

        # If there were no errors, then we try to delete dump_names
        if dump_errors == 0:
            keys = build_keys("dump_names", crashid)
            for key in keys:
                s3_delete_object(s3_client, bucket, key)

    # Delete processed crash
    keys = build_keys("processed_crash", crashid)
    for key in keys:
        obj = s3_fetch_object(s3_client, bucket, key)
        if obj:
            s3_delete_object(s3_client, bucket, key)


def get_es_crashstorage():
    """Return an Elasticsearch ConnectionContext."""
    return build_instance_from_settings(settings.CRASH_DESTINATIONS["es"])


def es_fetch_document(es_crashstorage, crashid):
    """Fetch a crash report document from Elasticsearch.

    :returns: Elasticsearch document as a dict or None

    """
    doc_type = es_crashstorage.get_doctype()

    with es_crashstorage.client() as conn:
        try:
            search = Search(using=conn, doc_type=doc_type)
            search = search.filter("term", **{"processed_crash.uuid": crashid})
            results = search.execute().to_dict()
            hits = results["hits"]["hits"]
            if hits:
                return hits[0]
        except Exception:
            logger.exception("ERROR: es: when fetching %s %s" % (doc_type, crashid))

    click.echo(f"es: not found: {doc_type} {crashid}")


def es_delete_document(es_crashstorage, index, doc_type, doc_id):
    """Delete document in Elasticsearch."""
    with es_crashstorage.client() as conn:
        try:
            conn.delete(index=index, doc_type=doc_type, id=doc_id)
            click.echo(f"es: deleted {index} {doc_type} {doc_id}")
        except Exception:
            logger.exception(
                "ERROR: es: when deleting %s %s %s" % (index, doc_type, doc_id)
            )


def es_delete(crashid):
    """Delete crash report data from Elasticsearch."""
    es_crashstorage = get_es_crashstorage()

    resp = es_fetch_document(es_crashstorage, crashid)
    if resp:
        es_delete_document(es_crashstorage, resp["_index"], resp["_type"], resp["_id"])


@click.command()
@click.argument("crashidsfile", nargs=1)
@click.pass_context
def cmd_permadelete(ctx, crashidsfile):
    """
    Permanently deletes crash report data from crash storage.

    The crashidsfile should be a complete path to the file with
    crashids in it--one per line. This will skip lines prefixed
    with a # treating them like comments.

    """
    if not os.path.exists(crashidsfile):
        click.echo(f"File {crashidsfile!r} does not exist.")
        return 1

    crashids = crashid_generator(crashidsfile)

    for crashid in crashids:
        click.echo(f"Working on {crashid!r}")
        s3_delete(crashid)
        es_delete(crashid)

    click.echo("Done!")


if __name__ == "__main__":
    cmd_permadelete()
