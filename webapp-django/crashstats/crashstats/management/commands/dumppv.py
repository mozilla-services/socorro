# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Dump the crashstats_productversion table as CSV.
"""

import csv
import io

from django.core.management.base import BaseCommand

from crashstats.crashstats.models import ProductVersion


class Command(BaseCommand):
    help = "Dump crashstats_productversion table as csv."

    def add_arguments(self, parser):
        parser.add_argument("outputfile", help="path to outputfile")

    def handle(self, **options):
        fn = options["outputfile"]

        pvs = ProductVersion.objects.order_by("id").values_list(
            "product_name",
            "release_channel",
            "major_version",
            "release_version",
            "version_string",
            "build_id",
            "archive_url",
        )

        string_buffer = io.StringIO()
        writer = csv.writer(string_buffer)
        for pv in pvs:
            writer.writerow(list(pv))

        lines = string_buffer.getvalue().splitlines()
        lines.sort()

        with open(fn, "w") as fp:
            fp.write("\n".join(lines) + "\n")
