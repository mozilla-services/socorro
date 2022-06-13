# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Test cron job command."""

    def add_arguments(self, parser):
        parser.add_argument("--run_time", help="Time to run for.")
        parser.add_argument("--crash", action="store_true", help="Crash when running.")
        parser.add_argument("--print", help="Value to print to stdout.")

    def handle(self, **options):
        if options["crash"]:
            raise Exception("**Sputter**")
        if options["print"]:
            self.stdout.write("To print: %r" % options["print"])
        self.stdout.write("This is a test.")
