from configman import Namespace
from socorro.cron.crontabber import PostgreSQLCronApp


class PGCronApp(PostgreSQLCronApp):
    app_name = 'pg-job'
    app_description = 'Does some foo things'

    def run(self, connection):
        print "DOING STUFF in", self.app_name
