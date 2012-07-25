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
    depends_on = (
        'ftpscraper',
        'reports-clean'
    )


class SignaturesCronApp(_MatViewBackfillBase):
    proc_name = 'update_signatures'
    app_name = 'signatures-matview'
    depends_on = ('reports-clean',)


class TCBSCronApp(_MatViewBackfillBase):
    proc_name = 'update_tcbs'
    app_name = 'tcbs-matview'
    depends_on = (
        'product-versions-matview',
        'signatures-matview',
        'os-versions-matview',
        'reports-clean'
    )


class ADUCronApp(_MatViewBackfillBase):
    proc_name = 'update_adu'
    app_name = 'adu-matview'
    depends_on = ('reports-clean',)


class HangReportCronApp(_MatViewBackfillBase):
    proc_name = 'update_hang_report'
    app_name = 'hang-report-matview'
    depends_on = ('reports-clean',)


class NightlyBuildsCronApp(_MatViewBackfillBase):
    proc_name = 'update_nightly_builds'
    app_name = 'nightly-builds-matview'
    depends_on = ('reports-clean',)


class BuildADUCronApp(_MatViewBackfillBase):
    proc_name = 'update_build_adu'
    app_name = 'build-adu-matview'
    depends_on = ('reports-clean',)


class CrashesByUserCronApp(_MatViewBackfillBase):
    proc_name = 'update_crashes_by_user'
    app_name = 'crashes-by-user-matview'
    depends_on = ('adu-matview',)
    depends_on = ('reports-clean',)


class CrashesByUserBuildCronApp(_MatViewBackfillBase):
    proc_name = 'update_crashes_by_user_build'
    app_name = 'crashes-by-user-build-matview'
    depends_on = (
        'build-adu-matview',
        'reports-clean'
    )


class CorrelationsCronApp(_MatViewBackfillBase):
    proc_name = 'update_correlations'
    app_name = 'correlations-matview'
    depends_on = ('reports-clean',)


class HomePageGraphCronApp(_MatViewBackfillBase):
    proc_name = 'update_home_page_graph'
    app_name = 'home-page-graph-matview'
    depends_on = (
        'product-adu-matview',
        'reports-clean',
    )


class HomePageGraphBuildCronApp(_MatViewBackfillBase):
    proc_name = 'update_home_page_graph_build'
    app_name = 'home-page-graph-matview-build'
    depends_on = (
        'build-adu-matview',
        'reports-clean',
    )


class TCBSBuildCronApp(_MatViewBackfillBase):
    proc_name = 'update_tcbs_build'
    app_name = 'tcbs-build-matview'
    depends_on = ('reports-clean',)


class ExplosivenessCronApp(_MatViewBackfillBase):
    proc_name = 'update_explosiveness'
    app_name = 'explosiveness-matview'
    depends_on = (
        'tcbs-matview',
        'build-adu-matview',
        'reports-clean'
    )
