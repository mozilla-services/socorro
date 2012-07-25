# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from socorro.cron.crontabber import PostgresBackfillCronApp


class ReportsCleanCronApp(PostgresBackfillCronApp):
    app_name = 'reports-clean'
    app_version = '1.0'
    app_description = ""
    depends_on = ('duplicates',)

    def run(self, connection, date):
        cursor = connection.cursor()
        date -= datetime.timedelta(hours=2)
        cursor.callproc('update_reports_clean', [date])
        connection.commit()
