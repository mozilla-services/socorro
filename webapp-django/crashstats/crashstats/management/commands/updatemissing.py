# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
This command checks known missing crashes to see if they've since been processed.
"""

from django.core.management.base import BaseCommand

from crashstats.crashstats.configman_utils import get_s3_context
from crashstats.crashstats.management.commands.verifyprocessed import (
    is_in_s3,
    check_elasticsearch,
)
from crashstats.supersearch.models import SuperSearchUnredacted
from crashstats.crashstats.models import MissingProcessedCrash


class Command(BaseCommand):
    help = "Check known missing crashes to see if they've been processed."

    def check_past_missing(self):
        """Check the table for missing crashes and check to see if they exist."""
        s3_context = get_s3_context()
        bucket = s3_context.config.bucket_name
        s3_client = s3_context.build_client()

        supersearch = SuperSearchUnredacted()

        crash_ids = []

        crash_ids = MissingProcessedCrash.objects.filter(
            is_processed=False
        ).values_list("crash_id", flat=True)

        no_longer_missing = []

        for crash_id in crash_ids:
            if is_in_s3(s3_client, bucket, crash_id):
                missing = check_elasticsearch(supersearch, crash_id)
                if not missing:
                    no_longer_missing.append(crash_id)

        updated = 0
        if no_longer_missing:
            updated = MissingProcessedCrash.objects.filter(
                crash_id__in=no_longer_missing
            ).update(is_processed=True)

        self.stdout.write(
            "Updated %s missing crashes which have since been processed" % updated
        )

    def handle(self, **options):
        self.check_past_missing()
        self.stdout.write("Done!")
