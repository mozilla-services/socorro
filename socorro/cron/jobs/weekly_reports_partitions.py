from configman import Namespace
from socorro.cron.crontabber import PostgresCronApp


class WeeklyReportsPartitionsCronApp(PostgresCronApp):
    app_name = 'weekly-reports-partitions'
    app_description = """See
    http://socorro.readthedocs.org/en/latest/databaseadminfunctions.html#weekly
    -report-partitions
    See https://bugzilla.mozilla.org/show_bug.cgi?id=701253
    """

    required_config = Namespace()

    def run(self, connection):
        cursor = connection.cursor()
        cursor.callproc('weekly_report_partitions')
