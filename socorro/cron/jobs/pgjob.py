from socorro.cron.crontabber import PostgreSQLCronApp


class PGCronApp(PostgreSQLCronApp):
    app_name = 'pg-job'
    app_description = 'Does some foo things'

    def run(self, connection):
        cursor = connection.cursor()
        cursor.execute('select relname from pg_class')
        print len(cursor.fetchall()), "relations"
