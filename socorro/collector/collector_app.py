#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""the collector recieves crashes from the field"""

# This app can be invoked like this:
#     .../socorro/collector/collector_app.py --help
# replace the ".../" with something that makes sense for your environment
# set both socorro and configman in your PYTHONPATH

from socorrolib.app.generic_app import App, main
from socorro.webapi.class_partial import class_with_partial_init
from socorrolib.lib.converters import web_services_from_str

from configman import Namespace
from configman.converters import class_converter

# an app running under modwsgi needs to have a name at the module level called
# application.  The value is set in the App's 'main' function below.  Only the
# wsgi version actually makes use of this variable.
application = None


#==============================================================================
class BaseCollectorApp(App):
    app_name = 'collector'
    app_version = '5.0'
    app_description = __doc__

    #--------------------------------------------------------------------------
    # in this section, define any configuration requirements
    required_config = Namespace()

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


#==============================================================================
class CollectorApp(BaseCollectorApp):
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
        'collector_class',
        default='socorro.collector.wsgi_breakpad_collector.BreakpadCollector',
        doc='the name of the class that handles collection',
        from_string_converter=class_converter
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
    # metrics namespace
    #     the namespace is for config parameters for the metrics system
    #--------------------------------------------------------------------------
    required_config.namespace('metrics')
    required_config.metrics.add_option(
        'metrics_class',
        default='socorro.external.metrics_base.MetricsBase',
        doc='the class that implements metrics; no value means no metrics',
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
        default='socorro.external.fs.crashstorage'
                '.FSLegacyDatedRadixTreeStorage',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def main(self):
        # modwsgi requires a module level name 'application'
        global application

        services_list = (
            self.config.collector.collector_class,
        )
        self.config.crash_storage = self.config.storage.crashstorage_class(
            self.config.storage
        )
        self.config.throttler = self.config.throttler.throttler_class(
            self.config.throttler
        )
        self.config.metrics = self.config.metrics.metrics_class(
            self.config.metrics
        )
        self.web_server = self.config.web_server.wsgi_server_class(
            self.config,  # needs the whole config not the local namespace
            services_list
        )

        # for modwsgi the 'run' method returns the wsgi function that the web
        # server will use.  For other webservers, the 'run' method actually
        # starts the standalone web server.
        application = self.web_server.run()


#==============================================================================
class Collector2015App(BaseCollectorApp):
    #--------------------------------------------------------------------------
    # in this section, define any configuration requirements
    required_config = Namespace()

    #--------------------------------------------------------------------------
    # services namespace
    #     the namespace is for config parameters about how to interpret
    #     crash submissions
    #--------------------------------------------------------------------------
    required_config.namespace('services')
    required_config.services.add_option(
        'services_controller',
        default='''[
        {
            "name": "collector",
            "uri": "/submit",
            "service_implementation_class":
            "socorro.collector.wsgi_breakpad_collector.BreakpadCollector2015"
        },
        {
            "name": "generic",
            "uri": "/some/other/uri",
            "service_implementation_class":
                "socorro.collector.wsgi_generic_collector.GenericCollector"
        }
        ]''',
        doc='json-like list of services to be offered by this collector:'
            '[{"name": sevice-name, "uri": uri, '
            '"service_implementation_class": class-name}, ...]',
        from_string_converter=web_services_from_str(),
    )

    #--------------------------------------------------------------------------
    def main(self):
        # modwsgi requires a module level name 'application'
        global application

        services_list = []
        # take the list of services that have been specified in the configman
        # setup and create a list of services appropriate for the wsgi server
        # class.  Ensure that each service has been coupled with its namespace
        # from the final configuration
        for namespace, uri, service_class in (
            self.config.services.services_controller.service_list
        ):
            services_list.append(
                # a tuple associating a URI with a service class
                (
                    uri,
                    # a binding of the service class with the configuration
                    # namespace for that service class
                    class_with_partial_init(
                        self.config.services[namespace]
                            .service_implementation_class,
                        self.config.services[namespace],
                        self.config
                    )
                )
            )

        # initialize the wsgi server with the list of URI/service impl tuples
        self.web_server = self.config.web_server.wsgi_server_class(
            self.config,  # needs the whole config not the local namespace
            services_list
        )

        # for modwsgi the 'run' method returns the wsgi function that the web
        # server will use.  For other webservers, the 'run' method actually
        # starts the standalone web server.
        application = self.web_server.run()

if __name__ == '__main__':
    main(CollectorApp)
