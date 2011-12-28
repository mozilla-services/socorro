#! /usr/bin/env python

"""demonstrates using configman to fetch algorithms and implementations"""

# This app can be invoked like this:
#     .../socorro/app/sampleApp.py --help
# set your path to make that simpler
# set both socorro and configman in your PYTHONPATH

import configman.config_manager as cm
import datetime


class ExampleApp(cm.RequiredConfig):
    app_name = 'sample'
    app_version = '0.1'
    app_doc = __doc__

    required_config = cm.Namespace()
    required_config.add_option('name',
                               default='Wilma',
                               doc='a name to echo')
    required_config.add_option('time',
                               default=datetime.datetime.now(),
                               doc='the time of day')

    def __init__(self, config):
        super(ExampleApp, self).__init__()
        self.config = config

    def main(self):
        # this is where we'd implement the app
        print 'hello, %s. The time is: %s' % (self.config.name,
                                              self.config.time)


if __name__ == '__main__':
    import socorro.app.generic_app as gapp
    gapp.main(ExampleApp)
