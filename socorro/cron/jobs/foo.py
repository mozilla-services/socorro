from configman import Namespace
from socorro.cron.crontabber import BaseCronApp


class FooCronApp(BaseCronApp):
    app_name = 'foo'
    app_description = 'Does some foo things'

    def run(self):
        print "DOING STUFF foo()"
