# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Tips on how to run this locally
-------------------------------

Run this:

    $ socorro-cmd crontabber --job=bugzilla-associations

To change the database config, use --help to see what the parameters are called.

"""

import datetime

from dateutil import tz
from configman import Namespace, class_converter

from socorro.cron.base import BaseCronApp
from socorro.lib.datetimeutil import utc_now
from socorro.lib.dbutil import (
    execute_query_fetchall,
    execute_no_results,
    SQLDidNotReturnSingleRow
)
from socorro.lib.requestslib import session_with_retries
from socorro.lib.transaction import transaction_context


# Query all bugs that changed since a given date, and that either were created
# or had their crash_signature field change. Only return the two fields that
# interest us, the id and the crash_signature text.
BUGZILLA_PARAMS = {
    'chfieldfrom': '%s',
    'chfieldto': 'Now',
    'chfield': ['[Bug creation]', 'cf_crash_signature'],
    'include_fields': ['id', 'cf_crash_signature'],
}
BUGZILLA_BASE_URL = 'https://bugzilla.mozilla.org/rest/bug'


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
    parts = content.split('[@')

    # NOTE(willkg): Because we use split, the first item in the list is always
    # a non-signature--so skip it.
    for part in parts[1:]:
        try:
            last_bracket = part.rindex(']')
            signature = part[:last_bracket].strip()
            signatures.add(signature)
        except ValueError:
            # Raised if ']' is not found in the string. In that case, we
            # simply ignore this malformed part.
            pass
    return signatures


class BugzillaCronApp(BaseCronApp):
    """Updates Socorro's knowledge of which bugs cover which crash signatures

    This queries Bugzilla for all the bugs that were created or had their crash
    signature value changed during the specified period.

    For all the bugs in this group, it updates the crashstats_bugassociation
    table with the signatures and bug ids.

    """
    app_name = 'bugzilla-associations'
    app_description = 'Bugzilla Associations'
    app_version = '0.1'

    required_config = Namespace()
    required_config.add_option(
        'days_into_past',
        default=0,
        doc=(
            'number of days to look into the past for bugs (0 - use last '
            'run time, >0 ignore when it last ran successfully)'
        )
    )
    required_config.add_option(
        'database_class',
        default='socorro.external.postgresql.connection_context.ConnectionContext',
        from_string_converter=class_converter,
        reference_value_from='resource.postgresql'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.database = self.config.database_class(self.config)

    def run(self):
        # Figure out how far back we want to ask Bugzilla about
        if self.config.days_into_past:
            last_run = utc_now() - datetime.timedelta(days=self.config.days_into_past)

        else:
            try:
                # KeyError if it has never run successfully
                # TypeError if self.job_information is None
                last_run = self.job_information['last_success']
            except (KeyError, TypeError):
                # This job has never been run
                last_run = utc_now()

        # bugzilla runs on PST, so we need to communicate in its time zone
        PST = tz.gettz('PST8PDT')
        last_run_formatted = last_run.astimezone(PST).strftime('%Y-%m-%d')

        # Fetch recent relevant changes and iterate over them updating our
        # data set
        for bug_id, signature_set in self._iterator(last_run_formatted):
            self.update_bug_data(bug_id, signature_set)

    def update_bug_data(self, bug_id, signature_set):
        with transaction_context(self.database) as connection:
            self.logger.debug('bug %s: %s', bug_id, signature_set)

            # If there's no associated signatures, delete everything for this bug id
            if not signature_set:
                sql = """
                DELETE FROM crashstats_bugassociation WHERE bug_id = %s
                """
                execute_no_results(connection, sql, (bug_id,))
                return

            try:
                sql = """
                SELECT signature FROM crashstats_bugassociation WHERE bug_id = %s
                """
                signature_rows = execute_query_fetchall(connection, sql, (bug_id,))
                signatures_db = [x[0] for x in signature_rows]

                for signature in signatures_db:
                    if signature not in signature_set:
                        sql = """
                        DELETE FROM crashstats_bugassociation
                        WHERE signature = %s and bug_id = %s
                        """
                        execute_no_results(connection, sql, (signature, bug_id))
                        self.logger.info('association removed: %s - "%s"', bug_id, signature)

            except SQLDidNotReturnSingleRow:
                signatures_db = []

            for signature in signature_set:
                if signature not in signatures_db:
                    sql = """
                    INSERT INTO crashstats_bugassociation (signature, bug_id)
                    VALUES (%s, %s)
                    """
                    execute_no_results(connection, sql, (signature, bug_id))
                    self.logger.info('association added: %s - "%s"', bug_id, signature)

    def _iterator(self, from_date):
        # Fetch all the bugs that have been created or had the crash_signature
        # field changed since from_date
        payload = BUGZILLA_PARAMS.copy()
        payload['chfieldfrom'] = from_date
        # Use a 30-second timeout because Bugzilla is slow sometimes
        session = session_with_retries(default_timeout=30.0)
        r = session.get(BUGZILLA_BASE_URL, params=payload)
        if r.status_code < 200 or r.status_code >= 300:
            r.raise_for_status()
        results = r.json()

        # Yield each one as a (bug_id, set of signatures)
        for report in results['bugs']:
            yield (
                int(report['id']),
                find_signatures(report.get('cf_crash_signature', ''))
            )
