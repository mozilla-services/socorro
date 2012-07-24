# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from configman import Namespace
from socorro.cron.crontabber import PostgresCronApp
from socorro.lib.datetimeutil import utc_now


class UpdateADUsCronApp(PostgresCronApp):

    app_name = 'update-adus'
    app_version = '1.0'
    app_description = 'Call the update_adu stored procedure'

    def run(self, connection):
        start_time = (utc_now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        cursor = connection.cursor()
        cursor.callproc('update_adu', [start_time])
