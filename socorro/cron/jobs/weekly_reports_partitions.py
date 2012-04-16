from configman import Namespace
from socorro.cron.crontabber import PostgreSQLCronApp


class WeeklyReportsPartitionsCronApp(PostgreSQLCronApp):
    app_name = 'weekly-reports-partitions'
    app_description = """See
    http://socorro.readthedocs.org/en/latest/databaseadminfunctions.html#weekly
    -report-partitions
    See https://bugzilla.mozilla.org/show_bug.cgi?id=701253
    """

    required_config = Namespace()

    def run(self, connection):
        cursor = connection.cursor()
        cursor.execute('SELECT weekly_report_partitions()')
