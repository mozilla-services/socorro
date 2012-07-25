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


class _MatViewBackfillBase(PostgresBackfillCronApp, _Base):

    def run(self, connection, date):
        cursor = connection.cursor()
        target_date = (date - datetime.timedelta(days=1)).date()
        cursor.callproc(self.get_proc_name(), [target_date])

#------------------------------------------------------------------------------


class ProductVersionsCronApp(_MatViewBase):
    proc_name = 'update_product_versions'
    app_name = 'product-versions-matview'
    depends_on = ('ftpscraper',)


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


# TODO depends on raw_adu fill
class BuildADUCronApp(_MatviewBackfillBase):
    proc_name = 'update_build_adu'
    app_name = 'build-adu-matview'


# TODO depends on raw_adu fill
class ProductADUCronApp(_MatviewBackfillBase):
    proc_name = 'update_product_adu'
    app_name = 'product-adu-matview'


class CrashesByUserCronApp(_MatviewBackfillBase):
    proc_name = 'update_crashes_by_user'
    app_name = 'crashes-by-user-matview'
    depends_on = ('adu-matview',)


class CrashesByUserBuildCronApp(_MatviewBackfillBase):
    proc_name = 'update_crashes_by_user_build'
    app_name = 'crashes-by-user-build-matview'
    depends_on = ('build-adu-matview',)


class CorrelationsCronApp(_MatviewBackfillBase):
    proc_name = 'update_correlations'
    app_name = 'correlations-matview'


class HomePageGraphCronApp(_MatviewBackfillBase):
    proc_name = 'update_home_page_graph'
    app_name = 'home-page-graph-matview'
    depends_on = ('product-adu-matview',)


class HomePageGraphBuildCronApp(_MatviewBackfillBase):
    proc_name = 'update_home_page_graph_build'
    app_name = 'home-page-graph-matview-build'
    depends_on = ('build-adu-matview',)


class SignatureProductsCronApp(_MatviewBackfillBase):
    proc_name = 'update_signature_products'
    app_name = 'signatures-products-matview'


class SignatureProductsRollupCronApp(_MatviewBackfillBase):
    proc_name = 'update_signature_products_rollup'
    app_name = 'signatures-products-rollup-matview'


class TCBSBuildCronApp(_MatViewBackfillBase):
    proc_name = 'update_tcbs_build'
    app_name = 'tcbs-build-matview'


class ExplosivenessCronApp(_MatViewBackfillBase):
    proc_name = 'update_explosiveness'
    app_name = 'explosiveness-matview'
    depends_on = (
        'tcbs-matview',
        'build-adu-matview'
    )
