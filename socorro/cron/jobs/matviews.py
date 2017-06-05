# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from crontabber.base import BaseCronApp
from crontabber.mixins import (
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


class ADUCronApp(_MatViewBackfillBase):
    proc_name = 'update_adu'
    app_name = 'adu-matview'
    depends_on = ('fetch-adi-from-hive', 'reports-clean',)


class BuildADUCronApp(_MatViewBackfillBase):
    proc_name = 'update_build_adu'
    app_name = 'build-adu-matview'
    depends_on = ('fetch-adi-from-hive', 'reports-clean')


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


class RawUpdateChannelCronApp(_MatViewBackfillBase):
    proc_name = 'update_raw_update_channel'
    app_name = 'raw-update-channel-matview'
    app_version = '1.0'
    app_description = "Find new update_channels for B2G in reports"
