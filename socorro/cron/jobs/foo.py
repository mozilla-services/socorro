from configman import Namespace
from socorro.cron.crontabber import BaseCronApp


class FooCronApp(BaseCronApp):
    app_name = 'foo'
    app_description = 'Does some foo things'

    required_config = Namespace()
    # e.g.
    #required_config.add_option(
    #    'my_option',
    #    default='Must have a default',
    #    doc='Explanation of the option')

    def run(self):
        print "DOING STUFF foo()"
