#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Loads a processed crash by either crash ID or date from either
# GCS or S3 into Elasticsearch, depending on `settings.CRASH_SOURCE`,
# optionally skipping crashes already in Elasticsearch.

# Uses a variation of `check_crash_ids_for_date`
# from the `verifyprocessed` command in Crash Stats to get crash IDs from S3/GCS:
# https://github.com/mozilla-services/socorro/blob/3f39c6aaa7f294884f3261fd268e8084d5eec93a/webapp/crashstats/crashstats/management/commands/verifyprocessed.py#L77-L115

# Usage: ./bin/load_processed_crash_into_es.py [OPTIONS] [CRASH_ID | DATE]

import concurrent.futures
import datetime
from functools import partial
from isodate import parse_date
from more_itertools import chunked

import click

from socorro import settings
from socorro.external.es.super_search_fields import FIELDS
from socorro.external.es.supersearch import SuperSearch
from socorro.lib.libooid import date_from_ooid
from socorro.libclass import build_instance_from_settings

NUM_CRASHIDS_TO_FETCH = "all"
# Number of seconds until we decide a worker has stalled
WORKER_TIMEOUT = 15 * 60


def is_in_storage(crash_storage, crash_id):
    """Is the processed crash in storage."""
    return crash_storage.exists_object(f"v1/processed_crash/{crash_id}")


def get_threechars():
    """Generate all combinations of 3 hex digits."""
    chars = "0123456789abcdef"
    for x in chars:
        for y in chars:
            for z in chars:
                yield x + y + z


def check_elasticsearch(supersearch, crash_ids):
    """Checks Elasticsearch and returns list of missing crash ids.

    Crash ids should all be on the same day.

    """
    crash_ids = [crash_ids] if isinstance(crash_ids, str) else crash_ids
    crash_date = date_from_ooid(crash_ids[0])

    # The datestamp in the crashid doesn't match the processed date sometimes especially
    # when the crash came in at the end of the day.
    start_date = (crash_date - datetime.timedelta(days=5)).strftime("%Y-%m-%d")
    end_date = (crash_date + datetime.timedelta(days=5)).strftime("%Y-%m-%d")

    params = {
        "uuid": crash_ids,
        "date": [">=%s" % start_date, "<=%s" % end_date],
        "_columns": ["uuid"],
        "_facets": [],
        "_facets_size": 0,
        "_fields": FIELDS,
    }
    search_results = supersearch.get(**params)

    crash_ids_in_es = [hit["uuid"] for hit in search_results["hits"]]
    return set(crash_ids) - set(crash_ids_in_es)


def get_crashids_in_storage(page, only_missing_in_es):
    crash_source = build_instance_from_settings(settings.CRASH_SOURCE)
    crash_dest = build_instance_from_settings(settings.CRASH_DESTINATIONS["es"])

    in_crash_source_page = []
    missing_in_es_page = []
    # NOTE(bdanforth): Keys here look like /v1/raw_crash/DATE/CRASHID
    crash_ids = [item.split("/")[-1] for item in page]

    if not crash_ids:
        return []

    # Check crashstorage source first
    for crash_id in crash_ids:
        if is_in_storage(crash_source, crash_id):
            in_crash_source_page.append(crash_id)
        else:
            click.echo(f"Could not find processed crash for raw crash {crash_id}.")

    if only_missing_in_es:
        supersearch = SuperSearch(crash_dest)

        # Check Elasticsearch in batches
        for crash_ids_batch in chunked(in_crash_source_page, 100):
            missing_in_es_batch = check_elasticsearch(supersearch, crash_ids_batch)
            missing_in_es_page.extend(missing_in_es_batch)

        return list(set(missing_in_es_page))

    return in_crash_source_page


def check_crashids_for_date(date, only_missing_in_es, num_workers):
    """Check crash ids for a given date"""
    crash_source = build_instance_from_settings(settings.CRASH_SOURCE)

    crash_ids = []

    # Grab all the crash ids at the given date directory
    page_iterator = crash_source.list_objects_paginator(
        prefix=f"v1/raw_crash/{date}",
    )

    get_crashids = partial(
        get_crashids_in_storage, only_missing_in_es=only_missing_in_es
    )

    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        for result in executor.map(get_crashids, page_iterator, timeout=WORKER_TIMEOUT):
            crash_ids.extend(result)

    return crash_ids


def save_crash_to_es(crash_id):
    crash_source = build_instance_from_settings(settings.CRASH_SOURCE)
    crash_dest = build_instance_from_settings(settings.CRASH_DESTINATIONS["es"])
    try:
        processed_crash = crash_source.get_processed_crash(crash_id)
        crash_dest.save_processed_crash(None, processed_crash)
        return (
            f"Crash with ID {crash_id!r} loaded from {type(crash_source).__name__!r}."
        )
    except Exception as exc:
        return f"Unable to load crash with ID {crash_id!r} from {type(crash_source).__name__!r}; error: {exc}."


@click.command()
@click.option(
    "--date",
    default=None,
    type=str,
    help=("Date to load processed crashes from as YYYY-MM-DD. Defaults to None."),
)
@click.option(
    "--crash-id",
    default=None,
    type=str,
    help="A single crash ID to load into ES from the source. E.g. 64f9a777-771d-4db3-82fa-b9c190240430. Defaults to None.",
)
@click.option(
    "--num-workers",
    default=4,
    type=int,
    help="The number of workers to use to check for crash IDs in the crashstorage source. Defaults to 4.",
)
@click.option(
    "--only-missing-in-es",
    default=False,
    type=bool,
    help="Whether to load only those processed crashes that are present in the crashstorage source but missing in Elasticsearch. Defaults to False.",
)
@click.pass_context
def load_crashes(ctx, date, crash_id, num_workers, only_missing_in_es):
    """
    Loads processed crashes into Elasticsearch by crash source (S3 or GCS)
    and either crash ID or date.

    Must specify either CRASH_ID or DATE.

    """
    crash_ids = []

    if crash_id:
        crash_ids.append(crash_id)
    elif date:
        check_date = parse_date(date)
        if not check_date:
            raise click.ClickException(f"Unrecognized run_time format: {date}")

        check_date_formatted = check_date.strftime("%Y%m%d")
        click.echo(
            f"Checking for missing processed crashes for: {check_date_formatted}"
        )

        crash_ids = check_crashids_for_date(
            date=check_date_formatted,
            only_missing_in_es=only_missing_in_es,
            num_workers=num_workers,
        )
    else:
        raise click.BadParameter(
            "Neither date nor crash_id were provided. At least one must be provided.",
            ctx=ctx,
            param_hint=["date", "crash_id"],
        )

    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(
            executor.map(save_crash_to_es, crash_ids, timeout=WORKER_TIMEOUT)
        )
        click.echo(results)


if __name__ == "__main__":
    load_crashes()
