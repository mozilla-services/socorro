from configman import Namespace
from crontabber.base import BaseCronApp
from crontabber.mixins import (
    with_postgres_transactions,
    with_single_postgres_transaction,
)


@with_postgres_transactions()
@with_single_postgres_transaction()
class CleanMissingSymbolsCronApp(BaseCronApp):
    app_name = 'clean-missing-symbols'
    app_description = """
    See https://bugzilla.mozilla.org/show_bug.cgi?id=1278498

    By default we truncate to the last 7 days. Normally our general
    retention policy is a lot longer but the missing_symbols
    is only ever queried for the last day.
    """
    required_config = Namespace()
    required_config.add_option(
        'days_to_keep',
        default=5,
        doc='Number of days of missing symbols to keep in Postgres')

    def run(self, connection):
        cursor = connection.cursor()
        # Casting to date because stored procs in psql are strongly typed.
        assert self.config.days_to_keep > 0
        cursor.execute(
            """
            DELETE FROM missing_symbols
            WHERE date_processed < NOW() - INTERVAL '{} days'
            """.format(self.config.days_to_keep)
        )
