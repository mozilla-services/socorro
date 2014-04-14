# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from socorro.cron.base import BaseCronApp
from socorro.cron.mixins import (
    as_backfill_cron_app,
    with_postgres_transactions,
    with_single_postgres_transaction,
)


@with_postgres_transactions()
@with_single_postgres_transaction()
class _MatViewBase(BaseCronApp):

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

    def run(self, connection):
        self.run_proc(connection)


@as_backfill_cron_app
class _MatViewBackfillBase(_MatViewBase):

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
        'adu-matview',
        'reports-clean'
    )


class ReportsCleanCronApp(_MatViewBackfillBase):
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


class DuplicatesCronApp(_MatViewBackfillBase):
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
        'reports-clean'
    )


class SignatureSummaryProductsCronApp(_MatViewBackfillBase):
    proc_name = 'update_signature_summary_products'
    app_name = 'signature-summary-products-matview'
    depends_on = (
        'reports-clean',
        'product-versions-matview'
    )


class SignatureSummaryInstallationsCronApp(_MatViewBackfillBase):
    proc_name = 'update_signature_summary_installations'
    app_name = 'signature-summary-installations-matview'
    depends_on = (
        'reports-clean',
        'product-versions-matview'
    )


class SignatureSummaryUptimeCronApp(_MatViewBackfillBase):
    proc_name = 'update_signature_summary_uptime'
    app_name = 'signature-summary-uptime-matview'
    depends_on = (
        'reports-clean',
        'product-versions-matview'
    )


class SignatureSummaryOsCronApp(_MatViewBackfillBase):
    proc_name = 'update_signature_summary_os'
    app_name = 'signature-summary-uptime-os'
    depends_on = (
        'reports-clean',
        'product-versions-matview'
    )


class SignatureSummaryProcessTypeCronApp(_MatViewBackfillBase):
    proc_name = 'update_signature_summary_process_type'
    app_name = 'signature-summary-uptime-process-type'
    depends_on = (
        'reports-clean',
        'product-versions-matview'
    )


class SignatureSummaryArchitectureCronApp(_MatViewBackfillBase):
    proc_name = 'update_signature_summary_architecture'
    app_name = 'signature-summary-uptime-architecture'
    depends_on = (
        'reports-clean',
        'product-versions-matview'
    )


class SignatureSummaryFlashVersionCronApp(_MatViewBackfillBase):
    proc_name = 'update_signature_summary_flash_version'
    app_name = 'signature-summary-uptime-flash-version'
    depends_on = (
        'reports-clean',
        'product-versions-matview'
    )


class SignatureSummaryDeviceCronApp(_MatViewBackfillBase):
    proc_name = 'update_signature_summary_device'
    app_name = 'signature-summary-uptime-device'
    depends_on = (
        'reports-clean',
        'product-versions-matview'
    )


class SignatureSummaryGraphicsCronApp(_MatViewBackfillBase):
    proc_name = 'update_signature_summary_graphics'
    app_name = 'signature-summary-uptime-graphics'
    depends_on = (
        'reports-clean',
        'product-versions-matview'
    )


class AndroidDevicesCronApp(_MatViewBackfillBase):
    proc_name = 'update_android_devices'
    app_name = 'android-devices-matview'
    # Depends on raw_crashes being populated, but no jobs


class GraphicsDeviceCronApp(_MatViewBackfillBase):
    proc_name = 'update_graphics_devices'
    app_name = 'graphics-device-matview'


class CrashAduByBuildSignatureCronApp(_MatViewBackfillBase):
    proc_name = 'update_crash_adu_by_build_signature'
    app_name = 'update-crash-adu-by-build-signature'
    depends_on = (
        'adu-matview',
        'reports-clean',
        'build-adu-matview',
    )


class GCCrashes(_MatViewBackfillBase):
    proc_name = 'update_gccrashes'
    app_name = 'update-gccrashes'
    depends_on = (
        'reports-clean',
    )


class RawUpdateChannelCronApp(_MatViewBackfillBase):
    proc_name = 'update_raw_update_channel'
    app_name = 'raw-update-channel-matview'
    app_version = '1.0'
    app_description = "Find new update_channels for B2G in reports"
