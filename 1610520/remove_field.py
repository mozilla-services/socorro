# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Given a set of crash reports via a file and a list of fields to remove, removes the
fields from the raw crash file in S3 and the document in Elasticsearch.

Usage:

    python 1610520/remove_field.py CRASHIDSFILE FIELD [FIELD...]

"""

import argparse
import concurrent.futures
from functools import partial
import io
import json
import logging
import os
import sys

from botocore.client import ClientError
from configman import ConfigurationManager
from configman.environment import environment
from elasticsearch_dsl import Search
from more_itertools import chunked

from socorro.external.boto.connection_context import S3Connection
from socorro.external.boto.crashstorage import dict_to_str
from socorro.external.es.connection_context import ConnectionContext
from socorro.lib.ooid import date_from_ooid
from socorro.lib.util import retry


# Total number of workers (processes) to run
MAX_WORKERS = 20

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


def wait_times_access():
    """Return generator for wait times between failed load/save attempts."""
    for i in [1, 1, 1, 1, 1]:
        yield i


@retry(
    retryable_exceptions=[ClientError],
    wait_time_generator=wait_times_access,
    module_logger=logger,
)
def fix_data_in_s3(fields, bucket, s3_client, crashid):
    """Fix data in raw_crash file in S3."""
    path = (
        "v2/raw_crash/%(entropy)s/%(date)s/%(crashid)s"
        % {
            "entropy": crashid[:3],
            "date": date_from_ooid(crashid).strftime("%Y%m%d"),
            "crashid": crashid
        }
    )
    resp = s3_client.get_object(Bucket=bucket, Key=path)
    raw_crash_as_string = resp["Body"].read()
    data = json.loads(raw_crash_as_string)
    should_save = False
    for field in fields:
        if field in data:
            del data[field]
            should_save = True

    if should_save:
        s3_client.upload_fileobj(
            Fileobj=io.BytesIO(dict_to_str(data).encode("utf-8")), Bucket=bucket, Key=path
        )
        print("# s3: fixed raw crash")
    else:
        print("# s3: raw crash was fine")


def fix_data_in_es(fields, es_conn, crashid):
    """Fix document in Elasticsearch."""
    doc_type = es_conn.get_doctype()
    with es_conn() as conn:
        search = Search(using=conn, doc_type=doc_type)
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
            conn.index(
                index=index, doc_type=doc_type, body=document, id=document_id
            )
            print("# es: fixed document")
        else:
            print("# es: document was fine")


def fix_data(crashids, fields):
    s3_context = get_s3_context()
    bucket = s3_context.config.bucket_name
    s3_client = s3_context.client

    es_conn = get_es_conn()

    for crashid in crashids:
        print("# working on %s" % crashid)

        # Fix the data in S3 and then Elasticsearch
        try:
            fix_data_in_s3(fields, bucket, s3_client, crashid)
            fix_data_in_es(fields, es_conn, crashid)
        except Exception:
            # If this throws an exception, print it out and move on. Then we'll finish
            # all the fixing for the first pass and can address the problematic crash
            # reports in a second pass.
            logger.exception("COUGH")


def main():
    parser = argparse.ArgumentParser(
        description="Remove a field from raw crash data on S3 and Elasticsearch."
    )
    parser.add_argument(
        "--parallel", action="store_true", help="Whether to run in parallel."
    )
    parser.add_argument(
        "crashidsfile", nargs=1, help="Path to the file with crashids in it."
    )
    parser.add_argument(
        "field", nargs="+", help="Fields to remove."
    )

    args = parser.parse_args()
    crashidsfile = args.crashidsfile[0]
    if not os.path.exists(crashidsfile):
        print("File %s does not exist." % crashidsfile)
        return 1

    with open(crashidsfile, "r") as fp:
        lines = fp.readlines()

    # Remove whitespace and lines that start with "#"
    crashids = [line.strip() for line in lines if not line.startswith("#")]
    print("# Total crash ids to fix: %s" % len(crashids))

    crashids_chunked = chunked(crashids, CHUNK_SIZE)
    fix_data_with_fields = partial(fix_data, fields=args.field)

    print("# num workers: %s" % MAX_WORKERS)
    if not args.parallel:
        print("# Running single-process.")
        list(map(fix_data_with_fields, crashids_chunked))
    else:
        print("# Running multi-process.")
        with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(fix_data_with_fields, crashids_chunked, timeout=WORKER_TIMEOUT)

    print("# Done!")


if __name__ == "__main__":
    sys.exit(main())
