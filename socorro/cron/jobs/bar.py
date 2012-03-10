from socorro.cron.crontabber import BaseCronApp


class BarCronApp(BaseCronApp):
    app_name = 'bar'
    app_description = 'Does some bar things'
    depends_on = 'foo'  # string, tuple or list

    def run(self):
        raise NameError('doesnotexist')
        print "DOING STUFF bar()"
