# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from socorro.cron.crontabber import PostgresCronApp, PostgresBackfillCronApp


class _Base(object):

    app_version = '1.0'  # default
    app_description = "Run certain matview stored procedures"

    def get_proc_name(self):
        return self.proc_name


class _MatViewBase(PostgresCronApp, _Base):

    def run(self, connection):
        cursor = connection.cursor()
        cursor.callproc(self.get_proc_name())
        connection.commit()


class _MatViewBackfillBase(PostgresBackfillCronApp, _Base):

    def run(self, connection, date):
        cursor = connection.cursor()
        target_date = (date - datetime.timedelta(days=1)).date()
        cursor.callproc(self.get_proc_name(), [target_date])
        connection.commit()

#------------------------------------------------------------------------------


class ProductVersionsCronApp(_MatViewBase):
    proc_name = 'update_product_versions'
    app_name = 'product-versions-matview'


class SignaturesCronApp(_MatViewBackfillBase):
    proc_name = 'update_signatures'
    app_name = 'signatures-matview'


class OSVersionsCronApp(_MatViewBackfillBase):
    proc_name = 'update_os_versions'
    app_name = 'os-versions-matview'


class TCBSCronApp(_MatViewBackfillBase):
    proc_name = 'update_tcbs'
    app_name = 'tcbs-matview'
    depends_on = (
        'product-versions-matview',
        'signatures-matview',
        'os-versions-matview'
    )


class ADUCronApp(_MatViewBackfillBase):
    proc_name = 'update_adu'
    app_name = 'adu-matview'


class DailyCrashesCronApp(_MatViewBackfillBase):
    proc_name = 'update_daily_crashes'
    app_name = 'daily-crashes-matview'
    depends_on = (
        'product-versions-matview',
        'signatures-matview',
    )


class HangReportCronApp(_MatViewBackfillBase):
    proc_name = 'update_hang_report'
    app_name = 'hang-report-matview'


class RankCompareCronApp(_MatViewBackfillBase):
    proc_name = 'update_rank_compare'
    app_name = 'rank-compare-matview'


class NightlyBuildsCronApp(_MatViewBackfillBase):
    proc_name = 'update_nightly_builds'
    app_name = 'nightly-builds-matview'
