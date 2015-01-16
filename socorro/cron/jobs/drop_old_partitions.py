# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from crontabber.base import BaseCronApp
from crontabber.mixins import (
    with_postgres_transactions,
    with_single_postgres_transaction,
)


@with_postgres_transactions()
@with_single_postgres_transaction()
class DropOldPartitionsCronApp(BaseCronApp):
    app_name = 'drop-old-partitions'
    app_version = '1.0'
    app_description = """See
    http://socorro.readthedocs.org/en/latest/development
    /databaseadminfunctions.html#drop-old-partitions
    See https://bugzilla.mozilla.org/show_bug.cgi?id=1014128
    """

    def run(self, connection):
        # Determine date from one year ago.
        one_year_ago = datetime.utcnow() - relativedelta(years=1)

        # Determine delta between previous Monday and year-old-date.
        delta_previous_monday = 0 - one_year_ago.weekday()

        # Determine date of Monday preceeding year-old-date.
        # This is an add operation but of a negative value, so subtraction.
        year_old_monday = one_year_ago + timedelta(days=delta_previous_monday)

        # Generate the cutoffdate string for the stored proc.
        cut_off_date = year_old_monday.date()

        cursor = connection.cursor()
        # Casting to date because stored procs in psql are strongly typed.
        cursor.execute(
            "select drop_named_partitions(%s)", (cut_off_date,)
        )
