# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from socorro.cron.crontabber import PostgresBackfillCronApp


class DuplicatesCronApp(PostgresBackfillCronApp):
    app_name = 'duplicates'
    app_version = '1.0'
    app_description = ""

    def run(self, connection, date):
        cursor = connection.cursor()
        start_time = date - datetime.timedelta(hours=3)
        end_time = start_time + datetime.timedelta(hours=1)
        cursor.callproc('update_reports_duplicates', [start_time, end_time])
        connection.commit()

        start_time += datetime.timedelta(minutes=30)
        end_time = start_time + datetime.timedelta(hours=1)
        cursor.callproc('update_reports_duplicates', [start_time, end_time])
        connection.commit()
