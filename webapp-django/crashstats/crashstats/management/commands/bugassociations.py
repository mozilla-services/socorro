# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Updates Socorro's knowledge of which bugs cover which crash signatures

This queries Bugzilla for all the bugs that were created or had their crash
signature value changed during the specified period.

For all the bugs in this group, it updates the BugAssociation data with the
signatures and bug ids.
"""

import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from crashstats.crashstats.models import BugAssociation
from socorro.lib.requestslib import session_with_retries


# Query all bugs that changed since a given date, and that either were created
# or had their crash_signature field change. Only return the two fields that
# interest us, the id and the crash_signature text.
BUG_QUERY_PARAMS = {
    "chfieldfrom": "%s",
    "chfieldto": "Now",
    "chfield": ["[Bug creation]", "cf_crash_signature"],
    "include_fields": ["id", "cf_crash_signature"],
}


def find_signatures(content):
    """Return a set of signatures found inside a string

    Signatures are found between `[@` and `]`. There can be any number of them
    in the content.

    Example:

    >>> find_signatures("some [@ signature] [@ another] and [@ even::this[] ]")
    set(['signature', 'another', 'even::this[]'])

    """
    if not content:
        return set()

    signatures = set()
    parts = content.split("[@")

    # NOTE(willkg): Because we use split, the first item in the list is always
    # a non-signature--so skip it.
    for part in parts[1:]:
        try:
            last_bracket = part.rindex("]")
            signature = part[:last_bracket].strip()
            signatures.add(signature)
        except ValueError:
            # Raised if ']' is not found in the string. In that case, we
            # simply ignore this malformed part.
            pass
    return signatures


class Command(BaseCommand):
    help = "Updates Socorro's knowledge of which bugs cover which crash signatures"

    def add_arguments(self, parser):
        parser.add_argument(
            "--last-success",
            default="",
            help=(
                "The start of the window to look at in YYYY-mm-dd format. Defaults to "
                "now minus one day."
            ),
        )

    def handle(self, **options):
        start_date_arg = options.get("last_success")
        if not start_date_arg:
            # Default to now minus a day
            start_date = timezone.now() - datetime.timedelta(days=1)
        else:
            # Try to parse it as a datetime
            start_date = parse_datetime(start_date_arg)
            if not start_date:
                # Try to parse it as a date
                start_date = parse_date(start_date_arg)
            if not start_date:
                raise CommandError(
                    "Unrecognized last_success format: %s" % start_date_arg
                )

        start_date_formatted = start_date.strftime("%Y-%m-%d")

        # Fetch recent relevant changes and iterate over them updating our
        # data set
        for bug_id, signature_set in self._iterator(start_date_formatted):
            self.update_bug_data(bug_id, signature_set)

    def update_bug_data(self, bug_id, signature_set):
        self.stdout.write("bug %s: %s" % (bug_id, signature_set))

        # If there's no associated signatures, delete everything for this bug id
        if not signature_set:
            BugAssociation.objects.filter(bug_id=bug_id).delete()
            return

        # Remove existing signature associations with this bug
        existing_signatures = list(
            BugAssociation.objects.filter(bug_id=bug_id).values_list(
                "signature", flat=True
            )
        )

        # Remove associations that no longer exist
        for signature in existing_signatures:
            if signature not in signature_set:
                BugAssociation.objects.filter(
                    bug_id=bug_id, signature=signature
                ).delete()
                self.stdout.write(
                    'association removed: %s - "%s"' % (bug_id, signature)
                )

        # Add new associations
        for signature in signature_set:
            if signature not in existing_signatures:
                BugAssociation.objects.create(bug_id=bug_id, signature=signature)
                self.stdout.write('association added: %s - "%s"' % (bug_id, signature))

    def _iterator(self, start_date):
        self.stdout.write("Working on %s to now" % start_date)
        # Fetch all the bugs that have been created or had the crash_signature
        # field changed since start_date
        payload = BUG_QUERY_PARAMS.copy()
        payload["chfieldfrom"] = start_date

        # Use a 30-second timeout because Bugzilla is slow sometimes
        session = session_with_retries(default_timeout=30.0)
        headers = {}
        if settings.BZAPI_TOKEN:
            headers["X-BUGZILLA-API-KEY"] = settings.BZAPI_TOKEN
            self.stdout.write(
                "using BZAPI_TOKEN (%s)" % (settings.BZAPI_TOKEN[:-8] + "xxxxxxxx")
            )
        else:
            self.stdout.write("Warning: No BZAPI_TOKEN specified!")
        r = session.get(
            settings.BZAPI_BASE_URL + "/bug", headers=headers, params=payload
        )
        if r.status_code < 200 or r.status_code >= 300:
            r.raise_for_status()
        results = r.json()

        # Yield each one as a (bug_id, set of signatures)
        for report in results["bugs"]:
            yield (
                int(report["id"]),
                find_signatures(report.get("cf_crash_signature", "")),
            )
