# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Maintain Signature data using crash data in Elasticsearch.
"""

import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from crashstats.crashstats.models import Signature
from crashstats.supersearch.models import SuperSearch
from crashstats.supersearch.libsupersearch import get_supersearch_fields
from socorro.lib.libdatetime import string_to_datetime


# Maximum number of results returned for a super search query
MAX_PAGE = 1000


class Command(BaseCommand):
    help = "Updates the signatures table using crash data from Elasticsearch"

    def add_arguments(self, parser):
        parser.add_argument(
            "--last-success",
            default="",
            help=(
                "The start of the window to look at in YYYY-mm-ddTHH:MM format in UTC. "
                "Defaults to run-time value minus 90 minutes."
            ),
        )
        parser.add_argument(
            "--run-time",
            default="",
            help=(
                "The end of the window to look at in YYYY-mm-ddTHH:MM format in UTC. "
                "Defaults to now."
            ),
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Whether or not to do a dry run."
        )

    def update_crashstats_signature(self, signature, report_date, report_build):
        report_build = int(report_build)
        report_date = string_to_datetime(report_date)
        try:
            sig = Signature.objects.get(signature=signature)
            sig.first_build = min(report_build, sig.first_build)
            sig.first_date = min(report_date, sig.first_date)
        except Signature.DoesNotExist:
            sig = Signature.objects.create(
                signature=signature, first_build=report_build, first_date=report_date
            )
        sig.save()

    def handle(self, **options):
        start_datetime = options.get("last_success")
        end_datetime = options.get("run_time")

        if end_datetime:
            end_datetime = parse_datetime(end_datetime)
        else:
            end_datetime = timezone.now()

        if start_datetime:
            start_datetime = parse_datetime(start_datetime)
            # When run via cronrun, start_datetime is based on the last success
            # and we want to increase the window by 10 minutes to get some
            # overlap with the previous run
            start_datetime = start_datetime - datetime.timedelta(minutes=10)
        else:
            # Default to end_datetime - 90 minutes
            start_datetime = end_datetime - datetime.timedelta(minutes=90)

        # Truncate seconds and microseconds
        start_datetime = start_datetime.replace(second=0, microsecond=0)
        end_datetime = end_datetime.replace(second=0, microsecond=0)

        if not end_datetime > start_datetime:
            raise CommandError("start time must be before end time.")

        # Do a super search and get the signature, buildid, and date processed for
        # every crash in the range
        all_fields = get_supersearch_fields()
        api = SuperSearch()
        self.stdout.write("Looking at %s to %s" % (start_datetime, end_datetime))

        params = {
            "date": [
                f">={start_datetime.isoformat()}",
                f"<{end_datetime.isoformat()}",
            ],
            "_columns": ["signature", "build_id", "date"],
            "_facets_size": 0,
            "_fields": all_fields,
            # Set up first page
            "_results_offset": 0,
            "_results_number": MAX_PAGE,
        }

        results = {}
        crashids_count = 0

        while True:
            resp = api.get(**params)
            hits = resp["hits"]
            for hit in hits:
                crashids_count += 1

                if not hit["build_id"]:
                    # Not all crashes have a build id, so skip the ones that don't.
                    continue

                if hit["signature"] in results:
                    data = results[hit["signature"]]
                    data["build_id"] = min(data["build_id"], hit["build_id"])
                    data["date"] = min(data["date"], hit["date"])
                else:
                    data = {
                        "signature": hit["signature"],
                        "build_id": hit["build_id"],
                        "date": hit["date"],
                    }
                results[hit["signature"]] = data

            # If there are no more crash ids to get, we return
            total = resp["total"]
            if not hits or crashids_count >= total:
                break

            # Get the next page, but only as many results as we need
            params["_results_offset"] += MAX_PAGE
            params["_results_number"] = min(
                # MAX_PAGE is the maximum we can request
                MAX_PAGE,
                # The number of results Super Search can return to us that is hasn't returned so far
                total - crashids_count,
            )

        signature_data = results.values()

        # Save signature data to the db
        for item in signature_data:
            if options["dry_run"]:
                self.stdout.write(
                    "Inserting/updating signature (%s, %s, %s)"
                    % (item["signature"], item["date"], item["build_id"])
                )
            else:
                self.update_crashstats_signature(
                    signature=item["signature"],
                    report_date=item["date"],
                    report_build=item["build_id"],
                )

        self.stdout.write("Inserted/updated %d signatures." % len(signature_data))
