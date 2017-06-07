# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import urllib2
import csv

from dateutil import tz
from configman import Namespace
from crontabber.base import BaseCronApp
from crontabber.mixins import with_postgres_transactions

from socorro.lib.datetimeutil import utc_now
from socorro.external.postgresql.dbapi2_util import (
    execute_query_fetchall,
    execute_no_results,
    SQLDidNotReturnSingleRow
)


_URL = (
    'https://bugzilla.mozilla.org/buglist.cgi?query_format=advanced&short_'
    'desc_type=allwordssubstr&short_desc=&long_desc_type=allwordssubstr&lo'
    'ng_desc=&bug_file_loc_type=allwordssubstr&bug_file_loc=&status_whiteb'
    'oard_type=allwordssubstr&status_whiteboard=&keywords_type=allwords&ke'
    'ywords=&deadlinefrom=&deadlineto=&emailassigned_to1=1&emailtype1=subs'
    'tring&email1=&emailassigned_to2=1&emailreporter2=1&emailqa_contact2=1'
    '&emailcc2=1&emailtype2=substring&email2=&bugidtype=include&bug_id=&vo'
    'tes=&chfieldfrom=%s&chfieldto=Now&chfield=[Bug+creation]&chfield=reso'
    'lution&chfield=bug_status&chfield=short_desc&chfield=cf_crash_signatu'
    're&chfieldvalue=&cmdtype=doit&order=Importance&field0-0-0=noop&type0-'
    '0-0=noop&value0-0-0=&columnlist=bug_id,cf_crash_signature&ctype=csv'
)


def find_signatures(content):
    """Return a list of signatures found inside a string.

    Signatures are found between `[@` and `]`. There can be any number of them
    in the content.

    Example:
    >>> "some [@ signature] [@ another_one] and [@ even::this[] ]"
    set(['signature', 'another_one', 'even::this[]'])
    """
    if not content:
        return set()

    signatures = set()
    parts = content.split('[@')
    for part in parts[1:]:
        try:
            last_bracket = part.rindex(']')
            signature = part[:last_bracket].strip()
            signatures.add(signature)
        except ValueError:
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
        'query',
        default=_URL,
        doc='Explanation of the option')

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
        query = self.config.query % last_run_formatted
        for (
            bug_id,
            signature_set
        ) in self._iterator(query):
            try:
                # each run of this loop is a transaction
                self.database_transaction_executor(
                    self.inner_transaction,
                    bug_id,
                    signature_set
                )
            except NothingUsefulHappened:
                pass

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

        useful = False

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
                    useful = True
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
                useful = True

        if not useful:
            raise NothingUsefulHappened('nothing useful done')

    def _iterator(self, query):
        for report in csv.DictReader(urllib2.urlopen(query)):
            yield (
                int(report['bug_id']),
                find_signatures(report['cf_crash_signature'])
            )
