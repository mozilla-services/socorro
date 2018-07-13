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
    """Runs update_product_versions stored procedure

    Updates product_versions and product_versions_builds tables from
    releases_raw table.

    """
    proc_name = 'update_product_versions'
    app_name = 'product-versions-matview'
