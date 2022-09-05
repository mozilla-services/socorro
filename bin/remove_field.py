#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Given a set of crash report ids via a file and a list of fields to remove, removes the
fields from the raw crash file in S3 and the document in Elasticsearch.

Usage::

    python bin/remove_field.py CRASHIDSFILE FIELD [FIELD...]

"""

import concurrent.futures
from functools import partial
import io
import json
import logging
import os

from botocore.client import ClientError
import click
from configman import ConfigurationManager
from configman.environment import environment
from elasticsearch.exceptions import ConnectionError
from elasticsearch_dsl import Search
from more_itertools import chunked

from socorro.external.boto.connection_context import S3Connection
from socorro.external.boto.crashstorage import build_keys, dict_to_str
from socorro.external.es.connection_context import ConnectionContext
from socorro.lib.util import retry


# Number of seconds until we decide a worker has stalled
WORKER_TIMEOUT = 15 * 60

# Number of crashids to hand to a worker to process in a single batch
CHUNK_SIZE = 1000


logger = logging.getLogger(__name__)


def get_s3_context():
    """Return an S3ConnectionContext."""
    cm = ConfigurationManager(
        S3Connection.get_required_config(), values_source_list=[environment]
    )
    config = cm.get_config()
    return S3Connection(config)


def get_es_conn():
    """Return an Elasticsearch ConnectionContext."""
    cm = ConfigurationManager(
        ConnectionContext.get_required_config(), values_source_list=[environment]
    )
    config = cm.get_config()
    return ConnectionContext(config)


def crashid_generator(fn):
    """Lazily yield crash ids."""
    with open(fn) as fp:
        for line in fp:
            line = line.strip()
            if line.startswith("#"):
                continue
            yield json.loads(line)


def wait_times_access():
    """Return generator for wait times between failed load/save attempts."""
    yield from [5, 5, 5, 5, 5]


@retry(
    retryable_exceptions=[ClientError],
    wait_time_generator=wait_times_access,
    module_logger=logger,
)
def fix_data_in_s3(fields, bucket, s3_client, crash_data):
    """Fix data in raw_crash file in S3."""
    crashid = crash_data["crashid"]

    # Iterate through the available keys until we find one we like.
    paths = build_keys("raw_crash", crashid)
    path = None
    for possible_path in paths:
        try:
            resp = s3_client.get_object(Bucket=bucket, Key=possible_path)
            path = possible_path
            break
        except s3_client.exceptions.NoSuchKey:
            continue

    if not path:
        # We're in a weird situation where we know there's a raw crash, but we can't
        # find it with the key options.
        raise Exception(f"raw crash not available at any keys: {paths}")

    raw_crash_as_string = resp["Body"].read()
    data = json.loads(raw_crash_as_string)
    should_save = False
    for field in fields:
        if field in data:
            del data[field]
            should_save = True

    if should_save:
        s3_client.upload_fileobj(
            Fileobj=io.BytesIO(dict_to_str(data).encode("utf-8")),
            Bucket=bucket,
            Key=path,
        )
        click.echo("# s3: fixed raw crash")
    else:
        click.echo("# s3: raw crash was fine")


@retry(
    retryable_exceptions=[ConnectionError],
    wait_time_generator=wait_times_access,
    module_logger=logger,
)
def fix_data_in_es(fields, es_conn, crash_data):
    """Fix document in Elasticsearch."""
    crashid = crash_data["crashid"]
    index = crash_data["index"]

    doc_type = es_conn.get_doctype()
    with es_conn() as conn:
        search = Search(using=conn, index=index, doc_type=doc_type)
        search = search.filter("term", **{"processed_crash.uuid": crashid})
        results = search.execute().to_dict()
        result = results["hits"]["hits"][0]
        index = result["_index"]
        document_id = result["_id"]
        document = result["_source"]

        should_save = False
        for field in fields:
            if field in document["raw_crash"]:
                should_save = True
                del document["raw_crash"][field]

        if should_save:
            conn.index(index=index, doc_type=doc_type, body=document, id=document_id)
            click.echo("# es: fixed document")
        else:
            click.echo("# es: document was fine")


def fix_data(crashids, fields):
    s3_context = get_s3_context()
    bucket = s3_context.config.bucket_name
    s3_client = s3_context.client

    es_conn = get_es_conn()

    for crashid in crashids:
        click.echo("# working on %s" % crashid)

        # Fix the data in S3 and then Elasticsearch
        try:
            fix_data_in_s3(fields, bucket, s3_client, crashid)
            fix_data_in_es(fields, es_conn, crashid)
        except Exception:
            # If this throws an exception, print it out and move on. Then we'll finish
            # all the fixing for the first pass and can address the problematic crash
            # reports in a second pass.
            logger.exception("Exception thrown with %s" % crashid)


@click.command()
@click.option(
    "--parallel/--no-parallel",
    default=False,
    show_default=True,
    help="Whether to run in parallel.",
)
@click.option(
    "--max-workers",
    type=int,
    default=20,
    show_default=True,
    help="Number of processes to run in parallel.",
)
@click.argument("crashidsfile", nargs=1)
@click.argument("fields", nargs=-1, required=True)
@click.pass_context
def cmd_remove_field(ctx, parallel, max_workers, crashidsfile, fields):
    """
    Remove a field from raw crash data on S3 and Elasticsearch.

    The crashidsfile is a path to a file with crash ids in it--one per line.
    Lines prefixed with # are treated as comments and are ignored.


    """
    if not os.path.exists(crashidsfile):
        click.echo("File %s does not exist." % crashidsfile)
        return 1

    crashids = crashid_generator(crashidsfile)
    crashids_chunked = chunked(crashids, CHUNK_SIZE)
    fix_data_with_fields = partial(fix_data, fields=fields)

    click.echo("# num workers: %s" % max_workers)
    if not parallel:
        click.echo("# Running single-process.")
        list(map(fix_data_with_fields, crashids_chunked))
    else:
        click.echo("# Running multi-process.")
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers
        ) as executor:
            executor.map(fix_data_with_fields, crashids_chunked, timeout=WORKER_TIMEOUT)

    click.echo("# Done!")


if __name__ == "__main__":
    cmd_remove_field()
