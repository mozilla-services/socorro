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
from traceback import print_exception

import click
from configman import ConfigurationManager
from configman.environment import environment
from elasticsearch_dsl import Search

from socorro.external.boto.connection_context import S3Connection
from socorro.external.boto.crashstorage import build_keys
from socorro.external.es.connection_context import ConnectionContext


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


def get_s3_context():
    """Return an S3ConnectionContext."""
    cm = ConfigurationManager(
        S3Connection.get_required_config(), values_source_list=[environment]
    )
    config = cm.get_config()
    return S3Connection(config)


def s3_delete_object(client, bucket, key):
    """Deletes a specific object from S3.

    Requires s3:DeleteObject.

    :return: True if the delete was fine or already not there; False if there was an
        error

    """
    try:
        client.delete_object(Bucket=bucket, Key=key)
        click.echo("s3: deleted %s" % key)
        return True
    except Exception:
        logger.exception("ERROR: s3: when deleting %s" % key)
        return False


def s3_fetch_object(client, bucket, key):
    """Fetch an object from S3 with appropriate handling for issues.

    Requires s3:GetObject.

    :returns: Body or None

    """
    try:
        resp = client.get_object(Bucket=bucket, Key=key)
        return resp["Body"].read()
    except client.exceptions.NoSuchKey:
        click.echo("s3: not found: %s" % key)
    except Exception:
        logger.exception("ERROR: s3: when fetching %s" % key)


def s3_delete(crashid):
    """Delete crash report data from S3."""
    s3_context = get_s3_context()
    bucket = s3_context.config.bucket_name
    s3_client = s3_context.client

    keys = build_keys("raw_crash", crashid)
    for key in keys:
        try:
            obj = s3_fetch_object(s3_client, bucket, key)
            if obj:
                s3_delete_object(s3_client, bucket, key)
        except Exception as exc:
            print(f"exception fetching/deleting raw crash: {key}")
            print_exception(exc)

    # Fetch dump_names which tells us which dumps exist
    key = build_keys("dump_names", crashid)[0]
    dump_names = s3_fetch_object(s3_client, bucket, key)
    if dump_names:
        try:
            dump_names = json.loads(dump_names)
        except Exception:
            logger.exception("ERROR: %s: s3: when parsing dump_names json" % crashid)
            dump_names = []

        # For each dump, delete it if it exists
        dump_errors = 0
        for dump_name in dump_names:
            # Handle dump_name -> key goofiness
            if dump_name in (None, "", "upload_file_minidump"):
                dump_name = "dump"
            key = build_keys(dump_name, crashid)[0]

            # If the dump is not there, that's fine; but if deleting the dump kicks up
            # an error, we want to make sure we don't delete dump_names.
            obj = s3_fetch_object(s3_client, bucket, key)
            if obj:
                if not s3_delete_object(s3_client, bucket, key):
                    dump_errors += 1

        # If there were no errors, then we try to delete dump_names
        if dump_errors == 0:
            key = build_keys("dump_names", crashid)[0]
            s3_delete_object(s3_client, bucket, key)

    # Delete processed crash
    key = build_keys("processed_crash", crashid)[0]
    obj = s3_fetch_object(s3_client, bucket, key)
    if obj:
        s3_delete_object(s3_client, bucket, key)


def get_es_conn():
    """Return an Elasticsearch ConnectionContext."""
    cm = ConfigurationManager(
        ConnectionContext.get_required_config(), values_source_list=[environment]
    )
    config = cm.get_config()
    return ConnectionContext(config)


def es_fetch_document(es_conn, crashid):
    """Fetch a crash report document from Elasticsearch.

    :returns: Elasticsearch document as a dict or None

    """
    doc_type = es_conn.get_doctype()

    with es_conn() as conn:
        try:
            search = Search(using=conn, doc_type=doc_type)
            search = search.filter("term", **{"processed_crash.uuid": crashid})
            results = search.execute().to_dict()
            hits = results["hits"]["hits"]
            if hits:
                return hits[0]
        except Exception:
            logger.exception("ERROR: es: when fetching %s %s" % (doc_type, crashid))

    click.echo("es: not found: %s %s" % (doc_type, crashid))


def es_delete_document(es_conn, index, doc_type, doc_id):
    """Delete document in Elasticsearch."""
    with es_conn() as conn:
        try:
            conn.delete(index=index, doc_type=doc_type, id=doc_id)
            click.echo("es: deleted %s %s %s" % (index, doc_type, doc_id))
        except Exception:
            logger.exception(
                "ERROR: es: when deleting %s %s %s" % (index, doc_type, doc_id)
            )


def es_delete(crashid):
    """Delete crash report data from Elasticsearch."""
    es_conn = get_es_conn()

    resp = es_fetch_document(es_conn, crashid)
    if resp:
        es_delete_document(es_conn, resp["_index"], resp["_type"], resp["_id"])


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
        click.echo("File %s does not exist." % crashidsfile)
        return 1

    crashids = crashid_generator(crashidsfile)

    for crashid in crashids:
        click.echo("Working on %s" % crashid)
        s3_delete(crashid)
        es_delete(crashid)

    click.echo("Done!")


if __name__ == "__main__":
    cmd_permadelete()
