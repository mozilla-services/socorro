from configman import Namespace
from crontabber.base import BaseCronApp
from crontabber.mixins import (
    with_postgres_transactions,
    with_single_postgres_transaction,
)


@with_postgres_transactions()
@with_single_postgres_transaction()
class CleanRawADICronApp(BaseCronApp):
    app_name = 'clean-raw-adi'
    app_description = """
    See https://bugzilla.mozilla.org/show_bug.cgi?id=1227131

    See https://mana.mozilla.org/wiki/pages/viewpage.action?pageId=5734601#cra\
    sh-stats.mozilla.com%28Socorro%29-DataExpirationPolicy
    """
    required_config = Namespace()
    required_config.add_option(
        'days_to_keep',
        default=30 * 6,  # rougly 6 months
        doc='Number of days of raw adi to keep in Postgres')

    def run(self, connection):
        cursor = connection.cursor()
        # Casting to date because stored procs in psql are strongly typed.
        assert self.config.days_to_keep > 0
        cursor.execute(
            """
            DELETE FROM raw_adi
            WHERE date < NOW() - INTERVAL '{} days'
            """.format(self.config.days_to_keep)
        )
