# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import sys

import requests
from dateutil import tz
from configman import Namespace
from configman.converters import class_converter
from crontabber.base import BaseCronApp
from crontabber.mixins import with_postgres_transactions

from socorro.lib.datetimeutil import utc_now
from socorro.app.socorro_app import App, main
from socorro.external.postgresql.dbapi2_util import (
    execute_query_fetchall,
    execute_no_results,
    SQLDidNotReturnSingleRow
)


# Query all bugs that changed since a given date, and that either where created
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
    """Return a list of signatures found inside a string.

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
    # The first item of this list is always not interesting, as it cannot
    # contain any signatures. We thus skip it.
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


class NothingUsefulHappened(Exception):
    """an exception to be raised when a pass through the inner loop has
    done nothing useful and we wish to induce a transaction rollback"""
    abandon_transaction = True


@with_postgres_transactions()
class BugzillaCronApp(BaseCronApp):
    app_name = 'bugzilla-associations'
    app_description = 'Bugzilla Associations'
    app_version = '0.1'

    required_config = Namespace()
    required_config.add_option(
        'days_into_past',
        default=0,
        doc='number of days to look into the past for bugs (0 - use last '
            'run time, >0 ignore when it last ran successfully)')

    def run(self):
        # if this is non-zero, we use it.
        if self.config.days_into_past:
            last_run = (
                utc_now() -
                datetime.timedelta(days=self.config.days_into_past)
            )
        else:
            try:
                # KeyError if it's never run successfully
                # TypeError if self.job_information is None
                last_run = self.job_information['last_success']
            except (KeyError, TypeError):
                # basically, the "virgin run" of this job
                last_run = utc_now()

        # bugzilla runs on PST, so we need to communicate in its time zone
        PST = tz.gettz('PST8PDT')
        last_run_formatted = last_run.astimezone(PST).strftime('%Y-%m-%d')
        for (
            bug_id,
            signature_set
        ) in self._iterator(last_run_formatted):
            # each run of this loop is a transaction
            self.database_transaction_executor(
                self.inner_transaction,
                bug_id,
                signature_set
            )

    def inner_transaction(
        self,
        connection,
        bug_id,
        signature_set
    ):
        self.config.logger.debug(
            "bug %s: %s",
            bug_id, signature_set
        )
        if not signature_set:
            execute_no_results(
                connection,
                "DELETE FROM bug_associations WHERE bug_id = %s",
                (bug_id,)
            )
            return

        try:
            signature_rows = execute_query_fetchall(
                connection,
                "SELECT signature FROM bug_associations WHERE bug_id = %s",
                (bug_id,)
            )
            signatures_db = [x[0] for x in signature_rows]

            for signature in signatures_db:
                if signature not in signature_set:
                    execute_no_results(
                        connection,
                        """
                        DELETE FROM bug_associations
                        WHERE signature = %s and bug_id = %s""",
                        (signature, bug_id)
                    )
                    self.config.logger.info(
                        'association removed: %s - "%s"',
                        bug_id, signature)
        except SQLDidNotReturnSingleRow:
            signatures_db = []

        for signature in signature_set:
            if signature not in signatures_db:
                execute_no_results(
                    connection,
                    """
                    INSERT INTO bug_associations (signature, bug_id)
                    VALUES (%s, %s)""",
                    (signature, bug_id)
                )
                self.config.logger.info(
                    'new association: %s - "%s"',
                    bug_id,
                    signature
                )

    def _iterator(self, from_date):
        payload = BUGZILLA_PARAMS.copy()
        payload['chfieldfrom'] = from_date
        r = requests.get(BUGZILLA_BASE_URL, params=payload)
        if r.status_code < 200 or r.status_code >= 300:
            r.raise_for_status()
        results = r.json()
        for report in results['bugs']:
            yield (
                int(report['id']),
                find_signatures(report.get('cf_crash_signature', ''))
            )


class BugzillaCronAppDryRunner(App):  # pragma: no cover
    """This class makes it possible to run the bugzilla crontabber app
    independently of running the whole of crontabber just to run this app.

    To run it, simply execute this file:

        $ python socorro/cron/jobs/bugzilla.py

    Note, this requires to actually be able to connect to a real Postgres
    table.

    Why not Mock? Because then it's hard to test if it really worked.

    You just need to make sure you have a Postgres db that has a
    `bug_associations` table. Then you can run it like this:

        $ python socorro/cron/jobs/bugzilla.py  \
        --database.dbname=mypostgresdatabase \
        --database.user=me \
        --database.password=secret

    """

    required_config = Namespace()
    required_config = Namespace()
    required_config.add_option(
        'days_into_past',
        default=1,
        doc='number of days to look into the past for bugs (0 - use last '
            'run time, >0 ignore when it last ran successfully)')
    required_config.add_option(
        'crontabber_job_class',
        default='socorro.cron.jobs.bugzilla.BugzillaCronApp',
        doc='not important',
        from_string_converter=class_converter,
    )

    def __init__(self, config):
        self.config = config
        self.app = config.crontabber_job_class(config, {})

    def main(self):
        self.app.run()


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(BugzillaCronAppDryRunner))
