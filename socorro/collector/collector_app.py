#! /usr/bin/env python
"""the collector recieves crashes from the field"""

# This app can be invoked like this:
#     .../socorro/collector/collector_app.py --help
# set your path to make that simpler
# set both socorro and configman in your PYTHONPATH

import datetime

from socorro.app.generic_app import App, main
from socorro.collector.wsgi_collector import Collector


from configman import Namespace
from configman.converters import class_converter

# an app running under modwsgi needs to have a name at the module level called
# application.  The value is set in the App's 'main' function below.  Only the
# modwsgi Apache version actually makes use of this variable.
application = None


#==============================================================================
class CollectorApp(App):
    app_name = 'collector'
    app_version = '4.0'
    app_description = __doc__

    #--------------------------------------------------------------------------
    # in this section, define any configuration requirements
    required_config = Namespace()

    #--------------------------------------------------------------------------
    # collector namespace
    #     the namespace is for config parameters about how to interpret
    #     crash submissions
    #--------------------------------------------------------------------------
    required_config.namespace('collector')
    required_config.collector.add_option(
        'dump_field',
        doc='the name of the form field containing the raw dump',
        default='upload_file_minidump'
    )
    required_config.collector.add_option(
        'dump_id_prefix',
        doc='the prefix to return to the client in front of the OOID',
        default='bp-'
    )

    #--------------------------------------------------------------------------
    # throttler namespace
    #     the namespace is for config parameters for the throttler system
    #--------------------------------------------------------------------------
    required_config.namespace('throttler')
    required_config.throttler.add_option(
        'throttler_class',
        default='socorro.collector.throttler.LegacyThrottler',
        doc='the class that implements the throttling action',
        from_string_converter=class_converter
    )
    #--------------------------------------------------------------------------
    # storage namespace
    #     the namespace is for config parameters crash storage
    #--------------------------------------------------------------------------
    required_config.namespace('storage')
    required_config.storage.add_option(
        'crashstorage_class',
        doc='the source storage class',
        default='socorro.external.filesystem.crashstorage.'
        'FileSystemRawCrashStorage',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    # web_server namespace
    #     the namespace is for config parameters the web server
    #--------------------------------------------------------------------------
    required_config.namespace('web_server')
    required_config.web_server.add_option(
        'wsgi_server_class',
        doc='a class implementing a wsgi web server',
        default='socorro.webapi.servers.CherryPy',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def main(self):
        # Apache modwsgi requireds a module level name 'applicaiton'
        global application

        services_list = (
            Collector,
        )
        self.config.crash_storage = self.config.storage.crashstorage_class(
            self.config.storage
        )
        self.config.throttler = self.config.throttler.throttler_class(
            self.config.throttler
        )
        self.web_server = self.config.web_server.wsgi_server_class(
            self.config,  # needs the whole config not the local namespace
            services_list
        )

        # for modwsgi the 'run' method returns the wsgi function that Apache
        # will use.  For other webservers, the 'run' method actually starts
        # the standalone web server.
        application = self.web_server.run()


if __name__ == '__main__':
    main(CollectorApp)