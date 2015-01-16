# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from crontabber.base import BaseCronApp
from crontabber.mixins import (
    with_postgres_transactions,
    with_single_postgres_transaction,
)


@with_postgres_transactions()
@with_single_postgres_transaction()
class WeeklyReportsPartitionsCronApp(BaseCronApp):
    app_name = 'weekly-reports-partitions'
    app_version = '1.0'
    app_description = """See
    http://socorro.readthedocs.org/en/latest/development
    /databaseadminfunctions.html#weekly-report-partitions
    See https://bugzilla.mozilla.org/show_bug.cgi?id=701253
    """

    def run(self, connection):
        cursor = connection.cursor()
        cursor.callproc('weekly_report_partitions')
