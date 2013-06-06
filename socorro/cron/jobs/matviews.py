# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from socorro.cron.base import PostgresCronApp, PostgresBackfillCronApp


class _Base(object):

    app_version = '1.0'  # default
    app_description = "Run certain matview stored procedures"

    def get_proc_name(self):
        return self.proc_name

    def run_proc(self, connection, signature=None):
        cursor = connection.cursor()
        if signature:
            cursor.callproc(self.get_proc_name(), signature)
            _calling = '%s(%r)' % (self.get_proc_name(), signature)
        else:
            cursor.callproc(self.get_proc_name())
            _calling = '%s()' % (self.get_proc_name(),)

        self.config.logger.info(
            'Result from calling %s: %r' %
            (_calling, cursor.fetchone())
        )
        if connection.notices:
            self.config.logger.info(
                'Notices from calling %s: %s' %
                (_calling, connection.notices)
            )

        connection.commit()


class _MatViewBase(PostgresCronApp, _Base):

    def run(self, connection):
        self.run_proc(connection)


class _MatViewBackfillBase(PostgresBackfillCronApp, _Base):

    def run(self, connection, date):
        target_date = (date - datetime.timedelta(days=1)).date()
        self.run_proc(connection, [target_date])

#------------------------------------------------------------------------------


class ProductVersionsCronApp(_MatViewBase):
    proc_name = 'update_product_versions'
    app_name = 'product-versions-matview'
    depends_on = (
        'reports-clean',
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
        'reports-clean',
    )


class ADUCronApp(_MatViewBackfillBase):
    proc_name = 'update_adu'
    app_name = 'adu-matview'
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
    depends_on = (
        'adu-matview',
        'reports-clean',
    )


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
        'adu-matview',
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


class ReportsCleanCronApp(PostgresBackfillCronApp, _Base):
    proc_name = 'update_reports_clean'
    app_name = 'reports-clean'
    app_version = '1.0'
    app_description = ""
    depends_on = (
        'duplicates',
    )

    def run(self, connection, date):
        date -= datetime.timedelta(hours=2)
        self.run_proc(connection, [date])


class DuplicatesCronApp(PostgresBackfillCronApp, _Base):
    proc_name = 'update_reports_duplicates'
    app_name = 'duplicates'
    app_version = '1.0'
    app_description = ""

    def run(self, connection, date):
        start_time = date - datetime.timedelta(hours=3)
        end_time = start_time + datetime.timedelta(hours=1)
        self.run_proc(connection, [start_time, end_time])

        start_time += datetime.timedelta(minutes=30)
        end_time = start_time + datetime.timedelta(hours=1)
        self.run_proc(connection, [start_time, end_time])


class ExploitabilityCronApp(_MatViewBackfillBase):
    proc_name = 'update_exploitability'
    app_name = 'exploitability-matview'
    depends_on = (
        'tcbs-matview',
        'build-adu-matview',
        'reports-clean'
    )
