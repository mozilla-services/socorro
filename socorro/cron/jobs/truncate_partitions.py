# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from crontabber.base import BaseCronApp
from crontabber.mixins import (
    with_postgres_transactions,
    with_single_postgres_transaction,
)


@with_postgres_transactions()
@with_single_postgres_transaction()
class TruncatePartitionsCronApp(BaseCronApp):
    app_name = 'truncate-partitions'
    app_version = '1.0'
    app_description = """See
    http://socorro.readthedocs.org/en/latest/databaseadminfunctions.html#truncate
    -partitions
    See https://bugzilla.mozilla.org/show_bug.cgi?id=1117911
    """

    def run(self, connection):
        # number of weeks of partitions to keep
        weeks = 2

        cursor = connection.cursor()
        # Casting to date because stored procs in psql are strongly typed.
        cursor.execute(
            "select truncate_partitions(%s)", (weeks,)
        )
