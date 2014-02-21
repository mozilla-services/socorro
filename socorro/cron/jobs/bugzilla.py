# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import urllib2
import csv

from dateutil import tz
from configman import Namespace
from socorro.database.database import singleRowSql, SQLDidNotReturnSingleRow
from socorro.cron.base import PostgresTransactionManagedCronApp


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
    '0-0=noop&value0-0-0=&columnlist=bug_id,bug_status,resolution,short_de'
    'sc,cf_crash_signature&ctype=csv'
)


class BugzillaCronApp(PostgresTransactionManagedCronApp):
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
            'run time)')

    def run(self, connection):
        # record_associations
        logger = self.config.logger

        try:
            # KeyError if it's never run successfully
            # TypeError if self.job_information is None
            last_run = self.job_information['last_success']
        except (KeyError, TypeError):
            last_run = (datetime.datetime.now(tz.gettz('UTC')) -
                        datetime.timedelta(days=self.config.days_into_past))

        PST = tz.gettz('PST8PDT')
        last_run_formatted = last_run.astimezone(PST).strftime('%Y-%m-%d')
        query = self.config.query % last_run_formatted
        cursor = connection.cursor()
        for i in self._iterator(query):
            bug_id, status, resolution, short_desc, signature_set = i
            logger.debug(
                "bug %s (%s, %s) %s: %s",
                bug_id, status, resolution, short_desc, signature_set)
            if not signature_set:
                cursor.execute("""
                DELETE FROM bugs WHERE id = %s
                """, (bug_id,))
                continue
            useful = False
            insert_made = False
            try:
                status_db, resolution_db, short_desc_db = singleRowSql(
                    cursor,
                    """
                    SELECT status, resolution, short_desc
                    FROM bugs
                    WHERE id = %s
                    """,
                    (bug_id,))
                if (status_db != status or resolution_db != resolution
                        or short_desc_db != short_desc):
                    cursor.execute(
                        """
                        UPDATE bugs SET
                          status = %s, resolution = %s, short_desc = %s
                        WHERE id = %s
                        """,
                        (status, resolution, short_desc, bug_id))
                    logger.info("bug status updated: %s - %s, %s",
                                bug_id, status, resolution)
                    useful = True

                cursor.execute(
                    """
                    SELECT signature FROM bug_associations WHERE bug_id = %s
                    """,
                    (bug_id,)
                )
                signatures_db = [x[0] for x in cursor.fetchall()]

                for signature in signatures_db:
                    if signature not in signature_set:
                        cursor.execute(
                            """
                            DELETE FROM bug_associations
                            WHERE signature = %s and bug_id = %s
                            """,
                            (signature, bug_id))
                        logger.info('association removed: %s - "%s"',
                                    bug_id, signature)
                        useful = True
            except SQLDidNotReturnSingleRow:
                cursor.execute(
                    """
                    INSERT INTO bugs
                    (id, status, resolution, short_desc)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (bug_id, status, resolution, short_desc))
                insert_made = True
                signatures_db = []

            for signature in signature_set:
                if signature not in signatures_db:
                    if self._has_signature_report(signature, cursor):
                        cursor.execute(
                            """
                            INSERT INTO bug_associations (signature, bug_id)
                            VALUES (%s, %s)
                            """,
                            (signature, bug_id))
                        logger.info('new association: %s - "%s"',
                                    bug_id, signature)
                        useful = True
                    else:
                        logger.info(
                            'rejecting association (no reports with this '
                            'signature): %s - "%s"',
                            bug_id,
                            signature)

            if useful:
                connection.commit()
                if insert_made:
                    logger.info('new bug: %s - %s, %s, "%s"',
                                bug_id, status, resolution, short_desc)
            else:
                connection.rollback()
                if insert_made:
                    logger.info('rejecting bug (no useful information): '
                                '%s - %s, %s, "%s"',
                                bug_id, status, resolution, short_desc)
                else:
                    logger.info('skipping bug (no new information): '
                                '%s - %s, %s, "%s"',
                                bug_id, status, resolution, short_desc)

    def _iterator(self, query):
        for report in csv.DictReader(urllib2.urlopen(query)):
            yield (
                int(report['bug_id']),
                report['bug_status'],
                report['resolution'],
                report['short_desc'],
                self._signatures_found(report['cf_crash_signature'])
            )

    def _signatures_found(self, signature):
        if not signature:
            return set()
        set_ = set()
        try:
            start = 0
            end = 0
            while True:
                start = signature.index("[@", end) + 2
                end = signature.index("]", end + 1)
                set_.add(signature[start:end].strip())
        except ValueError:
            # throw when index cannot match another sig, ignore
            pass
        return set_

    def _has_signature_report(self, signature, cursor):
        try:
            singleRowSql(
                cursor,
                """SELECT 1 FROM reports WHERE signature = %s LIMIT 1""",
                (signature,)
            )
            return True
        except SQLDidNotReturnSingleRow:
            return False
