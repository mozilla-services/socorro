#! /usr/bin/env python
"""demonstrates using configman to make a Socorro app"""

# This app can be invoked like this:
#     .../socorro/app/sampleApp.py --help
# set your path to make that simpler
# set both socorro and configman in your PYTHONPATH

import datetime

from socorro.app.generic_app import App, main

from configman import Namespace


#==============================================================================
class ExampleApp(App):
    app_name = 'sample'
    app_version = '0.1'
    app_description = __doc__

    #--------------------------------------------------------------------------
    # in this section, define any configuration requirements
    required_config = Namespace()
    required_config.add_option('name',
                               default='Wilma',
                               doc='a name to echo')
    required_config.add_option('time',
                               default=datetime.datetime.now(),
                               doc='the time of day')

    #--------------------------------------------------------------------------
    # implementing this constructor is only necessary when there is more
    # initialization to be done before main can be called
    #def __init__(self, config):
        #super(ExampleApp,self).__init__(config)

    #--------------------------------------------------------------------------
    def main(self):
        # this is where we'd implement the app
        # the configuraton is already setup as self.config
        print 'hello, %s. The time is: %s' % (self.config.name,
                                              self.config.time)


if __name__ == '__main__':
    main(ExampleApp)
