#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""implementation of the Socorro data service"""

# This app can be invoked like this:
#     .../socorro/middleware/middleware_app.py --help
# replace the ".../" with something that makes sense for your environment
# set both socorro and configman in your PYTHONPATH

from socorro.app.generic_app import App, main
from socorro.middleware.util import (
    classes_in_namespaces_converter,
)

from configman import Namespace
from configman.converters import class_converter

#------------------------------------------------------------------------------
# Here's the list of URIs mapping to classes and the files they belong to.
# The final lookup depends on the `implementation_list` option inside the app.
SERVICES_LIST = (
    'socorro.external.postgresql.bugs_service.Bugs,'
    'socorro.external.fs.crash_data_service.CrashData,'
    'socorro.external.postgresql.crash_service.Crash,'
    'socorro.external.postgresql.crashes_service.Crashes,'
    'socorro.external.postgresql.extensions_service.Extensions,'
    'socorro.external.postgresql.field_service.Field,'
    'socorro.external.postgresql.crash_trends_service.CrashTrends,'
    'socorro.external.postgresql.platforms_service.Platforms,'
    'socorro.external.rabbitmq.priorityjobs_service.Priorityjobs,'
    'socorro.external.postgresql.products_builds_service.ProductsBuilds,'
    'socorro.external.postgresql.products_service.Products,'
    'socorro.external.elasticsearch.query_service.Query,'
    'socorro.external.postgresql.releases_service.Releases,'
    'socorro.external.postgresql.signature_urls_service.SignatureURLs,'
    'socorro.external.postgresql.signature_summary_service'
        '.SignatureSummary,'
    'socorro.external.postgresql.search_service.Search,'
    'socorro.external.elasticsearch.supersearch_service.SuperSearch,'
    'socorro.external.postgresql.server_status_service.ServerStatus,'
    'socorro.external.postgresql.report_service.Report,'
    #'socorro.external.elasticsearch.report.Report,'  # suspect deprecated
    'socorro.external.postgresql.util_service.Util,'
    # this service ought to be implemented in crontabber, not postgres
    'socorro.external.postgresql.crontabber_state_service.CrontabberState,'
    'socorro.external.http.correlations.CorrelationsSignatures,'
    'socorro.external.http.correlations.Correlations,'
    'socorro.external.postgresql.skiplist_service.SkipList,'
    'socorro.external.postgresql.backfill_service.Backfill,'
    'socorro.external.postgresql.suspicious_service'
        '.SuspiciousCrashSignatures,'
    'socorro.external.postgresql.laglog_service.LagLog,'
    'socorro.external.postgresql.gccrashes_service.GCCrashes,'
    'socorro.external.postgresql.graphics_devices_service.GraphicsDevices'
)

# an app running under modwsgi needs to have a name at the module level called
# application.  The value is set in the App's 'main' function below.  Only the
# modwsgi Apache version actually makes use of this variable.
application = None


#==============================================================================
class MiddlewareApp(App):
    app_name = 'middleware'
    app_version = '4.0'  # return to original roots
    app_description = __doc__

    #--------------------------------------------------------------------------
    # in this section, define any configuration requirements
    required_config = Namespace()

    #--------------------------------------------------------------------------
    # web services namespace
    #     this namespace is for listing the services offered by the middleware
    #--------------------------------------------------------------------------
    required_config.namespace('services')
    required_config.services.add_option(
        'service_list',
        default=SERVICES_LIST,
        from_string_converter=classes_in_namespaces_converter()
    )

    #--------------------------------------------------------------------------
    # web_server namespace
    #     this namespace is for config parameters the web server
    #--------------------------------------------------------------------------
    required_config.namespace('web_server')
    required_config.web_server.add_option(
        'wsgi_server_class',
        doc='a class implementing a wsgi web server',
        default='socorro.webapi.servers.CherryPy',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    # sentry namespace
    #     this namespace is for Sentry error capturing with Raven
    #--------------------------------------------------------------------------
    required_config.namespace('sentry')
    required_config.sentry.add_option(
        'dsn',
        doc='DSN for Sentry via raven',
        default='',
        reference_value_from='secrets.sentry',
    )

    # because the socorro.webapi.servers classes bring up their own default
    # configurations like port number, the only way to override the default
    # is like this:
    from socorro.webapi.servers import StandAloneServer
    StandAloneServer.required_config.port.set_default(8883, force=True)

    #--------------------------------------------------------------------------
    def main(self):
        # Apache modwsgi requireds a module level name 'application'
        global application

        services_list = []
        # populate the 'services_list' with the tuples that will define the
        # urls and services offered by the middleware.
        for impl_class_namespace in (
            self.config.services.service_list.subordinate_namespace_names
        ):
            impl_class = self.config.services[impl_class_namespace].cls
            services_list.append(impl_class)

        self.web_server = self.config.web_server.wsgi_server_class(
            self.config,
            services_list
        )

        # for modwsgi the 'run' method returns the wsgi function that Apache
        # will use.  For other webservers, the 'run' method actually starts
        # the standalone web server.
        application = self.web_server.run()


#==============================================================================
if __name__ == '__main__':
    main(MiddlewareApp)
