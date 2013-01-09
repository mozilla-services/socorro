# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import Namespace
from socorro.cron.base import PostgresCronApp


class WeeklyReportsPartitionsCronApp(PostgresCronApp):
    app_name = 'weekly-reports-partitions'
    app_version = '1.0'
    app_description = """See
    http://socorro.readthedocs.org/en/latest/databaseadminfunctions.html#weekly
    -report-partitions
    See https://bugzilla.mozilla.org/show_bug.cgi?id=701253
    """

    required_config = Namespace()

    def run(self, connection):
        cursor = connection.cursor()
        cursor.callproc('weekly_report_partitions')
        connection.commit()
