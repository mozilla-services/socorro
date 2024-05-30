# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
This command verifies that all the incoming crash reports for the day before the
specified day were processed. It does this by listing the raw crash files for the day,
then checking to see if each of those raw crash files have corresponding processed crash
files.
"""

import concurrent.futures
import datetime
from functools import partial

from more_itertools import chunked

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import IntegrityError
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from crashstats.crashstats.models import MissingProcessedCrash, Reprocessing
from crashstats.supersearch.models import SuperSearchUnredacted
from socorro import settings as socorro_settings
from socorro.lib.libooid import date_from_ooid
from socorro.libclass import build_instance_from_settings
from socorro.libmarkus import METRICS


# Number of seconds until we decide a worker has stalled
WORKER_TIMEOUT = 15 * 60

# Number of prefix variations to pass to a check_crashids subprocess
CHUNK_SIZE = 4


def is_in_storage(crash_dest, crash_id):
    """Is the processed crash in storage."""
    return crash_dest.exists_object(f"v1/processed_crash/{crash_id}")


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
    }
    search_results = supersearch.get(**params)

    crash_ids_in_es = [hit["uuid"] for hit in search_results["hits"]]
    return set(crash_ids) - set(crash_ids_in_es)


def check_crashids_for_date(firstchars_chunk, date):
    """Check crash ids for a given firstchars and date"""
    crash_source = build_instance_from_settings(socorro_settings.CRASH_SOURCE)
    crash_dest = build_instance_from_settings(socorro_settings.STORAGE)

    supersearch = SuperSearchUnredacted()

    missing = []

    for firstchars in firstchars_chunk:
        # Grab all the crash ids at the given date directory
        page_iterator = crash_source.list_objects_paginator(
            prefix=f"v1/raw_crash/{date}/{firstchars}",
        )

        for page in page_iterator:
            # NOTE(willkg): Keys here look like /v1/raw_crash/DATE/CRASHID
            crash_ids = [item.split("/")[-1] for item in page]

            if not crash_ids:
                continue

            # Check storage first
            for crash_id in crash_ids:
                if not is_in_storage(crash_dest, crash_id):
                    missing.append(crash_id)

            # Check Elasticsearch in batches
            for crash_ids_batch in chunked(crash_ids, 100):
                missing_in_es = check_elasticsearch(supersearch, crash_ids_batch)
                missing.extend(missing_in_es)

    return list(set(missing))


class Command(BaseCommand):
    help = "Verify incoming crash reports were processed"

    def add_arguments(self, parser):
        parser.add_argument(
            "--run-time",
            default="",
            help="The day to check in YYYY-mm-dd format. Defaults to yesterday.",
        )
        parser.add_argument(
            "--num-workers",
            default=20,
            type=int,
            help="Number of concurrent workers to list raw_crashes.",
        )

    def get_threechars(self):
        """Generate all combinations of 3 hex digits."""
        chars = "0123456789abcdef"
        for x in chars:
            for y in chars:
                for z in chars:
                    yield x + y + z

    def find_missing(self, num_workers, date):
        check_crashids = partial(check_crashids_for_date, date=date)

        missing = []
        firstchars_chunked = chunked(self.get_threechars(), CHUNK_SIZE)

        if num_workers == 1:
            for result in map(check_crashids, firstchars_chunked):
                missing.extend(result)
        else:
            with concurrent.futures.ProcessPoolExecutor(
                max_workers=num_workers
            ) as executor:
                for result in executor.map(
                    check_crashids, firstchars_chunked, timeout=WORKER_TIMEOUT
                ):
                    missing.extend(result)

        return list(missing)

    def handle_missing(self, date, missing):
        """Report and reprocess crash ids for missing processed crashes."""
        METRICS.gauge("cron.verifyprocessed.missing_processed", len(missing))
        if missing:
            reprocessing_api = Reprocessing()
            for crash_id in missing:
                self.stdout.write(f"Missing: {crash_id}")

                try:
                    MissingProcessedCrash.objects.create(
                        crash_id=crash_id, is_processed=False
                    )
                except IntegrityError as ie:
                    if "violates unique constraint" in str(ie):
                        # If there's already one, that's fine
                        pass
                    else:
                        raise
                reprocessing_api.post(crash_ids=crash_id)

        else:
            self.stdout.write(f"All crashes for {date} were processed.")

    def handle(self, **options):
        check_date_arg = options.get("run_time")
        if check_date_arg:
            check_date = parse_datetime(check_date_arg)
            if not check_date:
                check_date = parse_date(check_date_arg)
            if not check_date:
                raise CommandError(f"Unrecognized run_time format: {check_date_arg}")
        else:
            check_date = timezone.now()

        # Look at the previous day because we want to look at a whole day.
        check_date = check_date - datetime.timedelta(days=1)

        check_date_formatted = check_date.strftime("%Y%m%d")
        self.stdout.write(
            f"Checking for missing processed crashes for: {check_date_formatted}"
        )

        # Find new missing crashes.
        missing = self.find_missing(options["num_workers"], check_date_formatted)
        self.handle_missing(check_date_formatted, missing)

        self.stdout.write("Done!")
