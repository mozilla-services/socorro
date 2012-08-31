#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""implementation of the Socorro data service"""

# This app can be invoked like this:
#     .../socorro/collector/middleware_app.py --help
# replace the ".../" with something that makes sense for your environment
# set both socorro and configman in your PYTHONPATH

import re
import os
import json
import web
from socorro.app.generic_app import App, main
from socorro.external import MissingOrBadArgumentError
from socorro.webapi.webapiService import JsonWebServiceBase
import socorro.services

from configman import Namespace, RequiredConfig
from configman.converters import class_converter
from socorro.external.postgresql.connection_context import ConnectionContext

#------------------------------------------------------------------------------
# Here's the list of URIs mapping to classes and the files they belong to.
# The final lookup depends on the `service_list` option inside the app.
SERVICES_LIST = (
    (r'/bugs/', 'bugs.Bugs'),
    (r'/crash/(.*)', 'crash.Crash'),
    (r'/crashes/(comments|daily|frequency|paireduuid|signatures)/(.*)', 'crashes.Crashes'),
    (r'/extensions/(.*)', 'extensions.Extensions'),
    (r'/crashtrends/(.*)', 'crash_trends.CrashTrends'),
    (r'/job/(.*)', 'job.Job'),
    (r'/priorityjobs/(.*)', 'priorityjobs.Priorityjobs'),
    (r'/products/builds/(.*)', 'products_builds.ProductsBuilds'),
    (r'/products/(.*)', 'products.Products'),
    (r'/releases/(featured)/(.*)', 'releases.Releases'),
    (r'/signatureurls/(.*)', 'signature_urls.SignatureURLs'),
    (r'/signaturesummary/(.*)', 'signature_summary.SignatureSummary'),
    (r'/search/(signatures|crashes)/(.*)', 'search.Search'),
    (r'/server_status/(.*)', 'server_status.ServerStatus'),
    (r'/report/(list)/(.*)', 'report.Report'),
    (r'/util/(versions_info)/(.*)', 'util.Util'),
)

# certain items in a URL path should NOT be split by `+`
DONT_TERM_SPLIT = re.compile("""
  \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2}
""", re.VERBOSE)

# an app running under modwsgi needs to have a name at the module level called
# application.  The value is set in the App's 'main' function below.  Only the
# modwsgi Apache version actually makes use of this variable.
application = None


class ImplementationConfigurationError(Exception):
    pass


class BadRequest(web.webapi.HTTPError):
    """The only reason to override this exception class here instead of using
    the one in web.webapi is so that we can pass a custom message into the
    exception so the client can get a hint of what went wrong.
    """
    def __init__(self, message="bad request"):
        status = "400 Bad Request"
        headers = {'Content-Type': 'text/html'}
        # can't use super() because it's an old-style class base
        web.webapi.HTTPError.__init__(self, status, headers, message)

#------------------------------------------------------------------------------
def items_list_converter(values):
    """Return a list of 2-pair tuples like this:
        [('key', 'value'), ...]
    from a string like this:
        'key: value, ...'
    """
    if not isinstance(values, basestring):
        raise TypeError('must be derivative of a basestring')
    return [[e.strip() for e in x.split(':')]
            for x in values.split(',') if x.strip()]


#==============================================================================
class MiddlewareApp(App):
    app_name = 'middleware'
    app_version = '3.0'
    app_description = __doc__

    services_list = []

    #--------------------------------------------------------------------------
    # in this section, define any configuration requirements
    required_config = Namespace()


    #--------------------------------------------------------------------------
    # implementations namespace
    #     the namespace is for external implementations of the services
    #-------------------------------------------------------------------------
    required_config.namespace('implementations')
    required_config.implementations.add_option(
        'service_list',
        doc='list of packages for service implementations',
        default='post:socorro.external.postgresql, '
                'hbase:socorro.external.hbase, '
                'elastic:socorro.external.elasticsearch',
        from_string_converter=items_list_converter
    )

    required_config.implementations.add_option(
        'service_overrides',
        doc='comma separated list of class overrides, e.g `Crashes: hbase`',
        default='', # e.g. 'Crashes: elastic',
        from_string_converter=items_list_converter
    )

    #--------------------------------------------------------------------------
    # database namespace
    #     the namespace is for external implementations of the services
    #-------------------------------------------------------------------------
    required_config.namespace('database')
    required_config.database.add_option(
        'database_class',
        default=ConnectionContext,
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    # webapi namespace
    #     this is all config options that used to belong to webapiconfig.py
    #-------------------------------------------------------------------------
    required_config.namespace('webapi')
    required_config.webapi.add_option(
        'elasticSearchHostname',
        default='localhost',
        doc='String containing the URI of the Elastic Search instance.'
    )
    required_config.webapi.add_option(
        'elasticSearchPort',
        default='9200',
        doc='String containing the port on which calling the Elastic '
            'Search instance.'
    )
    required_config.webapi.add_option(
        'searchMaxNumberOfDistinctSignatures',
        default=1000,
        doc='Integer containing the maximum allowed number of distinct '
            'signatures the system should retrieve. Used mainly for '
            'performances in ElasticSearch'
    )
    required_config.webapi.add_option(
        'platforms',
        default=[{
                "id" : "windows",
                "name" : "Windows NT"
            },
            {
                "id" : "mac",
                "name" : "Mac OS X"
            },
            {
                "id" : "linux",
                "name" : "Linux"
            },
        ],
        doc='Array associating OS ids to full names.'
    )
    required_config.webapi.add_option(
        'channels',
        default=['Beta', 'Aurora', 'Nightly', 'beta', 'aurora', 'nightly'],
        doc='List of release channels, excluding the `release` one.'
    )
    required_config.webapi.add_option(
        'restricted_channels',
        default=['Beta', 'beta'],
        doc='List of release channels to restrict based on build ids.'
    )

    #--------------------------------------------------------------------------
    # revisions namespace
    #     this is all config options that used to belong to revisionsconfig.py
    #--------------------------------------------------------------------------
    required_config.namespace('revisions')
    required_config.revisions.add_option(
        'socorro_revision',
        default='CURRENT_SOCORRO_REVISION',
        doc='the current revision of Socorro'
    )
    required_config.revisions.add_option(
        'breakpad_revision',
        default='CURRENT_BREAKPAD_REVISION',
        doc='the current revision of Breakpad'
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

        ## 1 turn these names of classes into real references to classes
        def lookup(file_and_class):
            file_name, class_name = file_and_class.rsplit('.', 1)
            overrides = dict(self.config.implementations.service_overrides)
            for prefix, base_module_path in self.config.implementations.service_list:
                if class_name in overrides:
                    if prefix != overrides[class_name]:
                        continue
                try:
                    module = __import__(
                        '%s.%s' % (base_module_path, file_name),
                        globals(),
                        locals(),
                        [class_name]
                    )
                except ImportError:
                    raise ImportError(
                        "Unable to import %s.%s.%s" %
                        (base_module_path, file_name, class_name)
                    )
                return getattr(module, class_name)
            raise ImplementationConfigurationError(file_and_class)

        services_list = ((x, lookup(y)) for x, y in SERVICES_LIST)

        ## 2 wrap each class with the ImplementationWrapper class
        def wrap(cls):
            return type(cls.__name__, (ImplementationWrapper,), {'cls': cls})
        services_list = ((x, wrap(y)) for x, y in services_list)

        self.web_server = self.config.web_server.wsgi_server_class(
            self.config,  # needs the whole config not the local namespace
            services_list
        )

        # for modwsgi the 'run' method returns the wsgi function that Apache
        # will use.  For other webservers, the 'run' method actually starts
        # the standalone web server.
        application = self.web_server.run()


class ImplementationWrapper(JsonWebServiceBase):

    def GET(self, *args, **kwargs):
        default_method = kwargs.pop('default_method', 'get')
        assert default_method in ('get', 'post', 'put'), default_method
        method_name = default_method
        if len(args) > 1:
            method_name = args[0]
        params = kwargs
        if len(args) > 0:
            params.update(self.parse_url_path(args[-1]))
        self._correct_signature_parameters(params)
        instance = self.cls(config=self.context)
        try:
            method = getattr(instance, method_name)
        except AttributeError:
            try:
                if method_name == 'post' and getattr(instance, 'create', None):
                    # use the `create` alias
                    method = instance.create
                elif method_name == 'put' and getattr(instance, 'update', None):
                    # use the `update` alias
                    method = instance.update
                else:
                    if method_name.startswith(default_method):
                        raise AttributeError
                    method = getattr(
                        instance,
                        '%s_%s' % (default_method, method_name)
                    )
            except AttributeError:
                self.context.logger.warning(
                    'The method %r does not exist on %r' %
                    (method_name, instance)
                )
                raise web.webapi.NoMethod(instance)
        try:
            result = method(**params)
            if isinstance(result, tuple):
                web.header('Content-Type', result[1])
                return result[0]
            web.header('Content-Type', 'application/json')
            dumped = json.dumps(result)
            web.header('Content-Length', len(dumped))
            return dumped

        except MissingOrBadArgumentError, msg:
            raise BadRequest(str(msg))

    def POST(self, *args, **kwargs):
        params = self._get_web_input_params()
        return self.GET(default_method='post', *args, **params)

    def PUT(self, *args, **kwargs):
        params = self._get_web_input_params()
        return self.GET(default_method='put', *args, **params)

    def _get_web_input_params(self, **extra):
        """Because of the stupidify of web.py we can't say that all just tell
        it to collect all POST or GET variables as arrays unless we explicitely
        list the defaults.

        So, try to look ahead at the class that will need the input and see
        if there are certain filters it expects to be lists.
        """
        defaults = {}
        for name, __, conversions in getattr(self.cls, 'filters', []):
            if conversions[0] == 'list':
                defaults[name] = []
        if extra is not None:
            defaults.update(extra)
        return web.input(**defaults)

    def _correct_signature_parameters(self, params):
        for key in ('signature', 'terms', 'signatures'):
            if key in params:
                params[key] = self.decode_special_characters(
                    params[key]
                )

    def parse_url_path(self, path):
        """
        Take a string of parameters and return a dictionary of key, value.

        Example 1:
            "param/value/"
            =>
            {
                "param": "value"
            }

        Example 2:
            "param1/value1/param2/value21+value22+value23/"
            =>
            {
                "param1": "value1",
                "param2": [
                    "value21",
                    "value22",
                    "value23"
                ]
            }

        Example 3:
            "param1/value1/param2/"
            =>
            {
                "param1": "value1"
            }

        """
        terms_sep = "+"
        params_sep = "/"

        args = path.split(params_sep)

        params = {}
        for i in range(0, len(args), 2):
            try:
                if args[i]:
                    params[args[i]] = args[i + 1]
            except IndexError:
                pass

        for key, value in params.iteritems():
            if value.count(terms_sep) and not DONT_TERM_SPLIT.match(value):
                params[key] = value.split(terms_sep)

        return params

    @staticmethod
    def decode_special_characters(value):
        """Return a decoded string or list of strings.

        Because characters '/' and '+' are special in our URL scheme, we need
        to double-encode them in the client. This function is to decode them
        so our service can use them as expected.
        """
        def convert(s):
            return s.replace("%2B", "+").replace("%2F", "/")

        if isinstance(value, (list, tuple)):
            return [convert(x) for x in value]

        assert isinstance(value, basestring)
        return convert(value)



if __name__ == '__main__':
    main(MiddlewareApp)
