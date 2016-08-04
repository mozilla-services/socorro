#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# This app can be invoked like this:
#     .../socorro/middleware/middleware_app.py --help
# replace the ".../" with something that makes sense for your environment
# set both socorro and configman in your PYTHONPATH

import cgi
import json
import re
import time

import web
import ujson

from socorrolib.app.generic_app import App, main
from socorrolib.lib import (
    MissingArgumentError,
    BadArgumentError,
    ResourceNotFound,
    ResourceUnavailable
)
from socorro.webapi.webapiService import (
    JsonWebServiceBase,
    Timeout,
    NotFound,
    BadRequest
)

import raven
from configman import Namespace
from configman.converters import class_converter

#------------------------------------------------------------------------------
# Here's the list of URIs mapping to classes and the files they belong to.
# The final lookup depends on the `implementation_list` option inside the app.
SERVICES_LIST = (
    (r'/backfill/(.*)', 'backfill.Backfill'),
    (r'/correlations/signatures/(.*)', 'correlations.CorrelationsSignatures'),
    (r'/correlations/(.*)', 'correlations.Correlations'),
    (r'/crash_data/(.*)', 'crash_data.CrashData'),
    (
        r'/crashes/'
        r'(comments|count_by_day|daily|frequency|signatures|'
        r'signature_history|exploitability|adu_by_signature)/(.*)',
        'crashes.Crashes'
    ),
    (r'/field/(.*)', 'field.Field'),
    (r'/priorityjobs/(.*)', 'priorityjobs.Priorityjobs'),
    (r'/products/(.*)', 'products.Products'),  # deprecated
    (r'/query/', 'query.Query'),
    (r'/releases/(channels|featured|release)/(.*)', 'releases.Releases'),
    (r'/report/(list)/(.*)', 'report.Report'),
    (r'/signaturesummary/(.*)', 'signature_summary.SignatureSummary'),
    (r'/signatureurls/(.*)', 'signature_urls.SignatureURLs'),
    (r'/util/(versions_info)/(.*)', 'util.Util'),
    (r'/healthcheck/', 'healthcheck.Healthcheck'),
)

# certain items in a URL path should NOT be split by `+`
DONT_TERM_SPLIT = re.compile("""
  \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2}
""", re.VERBOSE)

# an app running under modwsgi needs to have a name at the module level called
# application.  The value is set in the App's 'main' function below.  Only the
# wsgi version actually makes use of this variable.
application = None


class ImplementationConfigurationError(Exception):
    pass


#------------------------------------------------------------------------------
def items_list_decode(values):
    """Return a list of 2-pair tuples like this:
        [('key', 'value'), ...]
    from a string like this:
        'key: value, ...'
    """
    assert isinstance(values, basestring)
    return [[e.strip() for e in x.split(':')]
            for x in values.split(',') if x.strip()]


def items_list_encode(values):
    """From a nest iterator like [['one', 'One'], ...]
    return a string like 'one: One, ...'
    """
    assert isinstance(values, (list, tuple))
    return ', '.join(
        '%s: %s' % (one, two)
        for (one, two) in values
    )


def string_to_list(input_str):
    return [x.strip() for x in input_str.split(',') if x.strip()]


#==============================================================================
class MiddlewareApp(App):
    app_name = 'middleware'
    app_version = '3.1'
    app_description = __doc__

    # make the global list a class attribute
    SERVICES_LIST = SERVICES_LIST

    #--------------------------------------------------------------------------
    # in this section, define any configuration requirements
    required_config = Namespace()

    #--------------------------------------------------------------------------
    # implementations namespace
    #     the namespace is for external implementations of the services
    #-------------------------------------------------------------------------
    required_config.namespace('implementations')
    required_config.implementations.add_option(
        'implementation_list',
        doc='list of packages for service implementations',
        default='psql:socorro.external.postgresql, '
                'hbase:socorro.external.hb, '
                'es:socorro.external.es, '
                'fs:socorro.external.fs, '
                'http:socorro.external.http, '
                'rabbitmq:socorro.external.rabbitmq',
        from_string_converter=items_list_decode,
        to_string_converter=items_list_encode
    )

    required_config.implementations.add_option(
        'service_overrides',
        doc='comma separated list of class overrides, e.g `Crashes: hbase`',
        default='CrashData: fs, '
                'Correlations: http, '
                'CorrelationsSignatures: http, '
                'SuperSearch: es, '
                'Priorityjobs: rabbitmq, '
                'Query: es',
        from_string_converter=items_list_decode,
        to_string_converter=items_list_encode
    )

    #--------------------------------------------------------------------------
    # database namespace
    #     the namespace is for external implementations of the services
    #-------------------------------------------------------------------------
    required_config.namespace('database')
    required_config.database.add_option(
        'crashstorage_class',
        default='socorro.external.postgresql.crashstorage.'
                'PostgreSQLCrashStorage',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    # hbase namespace
    #     the namespace is for external implementations of the services
    #-------------------------------------------------------------------------
    required_config.namespace('hbase')
    required_config.hbase.add_option(
        'hbase_class',
        default='socorro.external.boto.crashstorage.BotoS3CrashStorage',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    # filesystem namespace
    #     the namespace is for external implementations of the services
    #-------------------------------------------------------------------------
    required_config.namespace('filesystem')
    required_config.filesystem.add_option(
        'filesystem_class',
        default='socorro.external.fs.crashstorage.FSLegacyRadixTreeStorage',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    # elasticsearch namespace
    #     the namespace is for external implementations of the services
    #-------------------------------------------------------------------------
    required_config.namespace('elasticsearch')
    required_config.elasticsearch.add_option(
        'elasticsearch_class',
        default='socorro.external.es.connection_context.ConnectionContext',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    # rabbitmq namespace
    #     the namespace is for external implementations of the services
    #-------------------------------------------------------------------------
    required_config.namespace('rabbitmq')
    required_config.rabbitmq.add_option(
        'rabbitmq_class',
        default='socorro.external.rabbitmq.connection_context.'
                'ConnectionContext',
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
        doc='String containing the URI of the Elastic Search instance.',
        reference_value_from='resource.elasticsearch',
    )
    required_config.webapi.add_option(
        'elasticSearchPort',
        default='9200',
        doc='String containing the port on which calling the Elastic '
            'Search instance.',
        reference_value_from='resource.elasticsearch',
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
        default=[
            {
                "id": "windows",
                "name": "Windows NT"
            },
            {
                "id": "mac",
                "name": "Mac OS X"
            },
            {
                "id": "linux",
                "name": "Linux"
            },
        ],
        doc='Array associating OS ids to full names.',
        from_string_converter=lambda x: json.loads(x)
    )
    required_config.webapi.add_option(
        'non_release_channels',
        default=['beta', 'aurora', 'nightly'],
        doc='List of channels, excluding the `release` one.',
        from_string_converter=string_to_list
    )
    required_config.webapi.add_option(
        'restricted_channels',
        default=['beta'],
        doc='List of channels to restrict based on build ids.',
        from_string_converter=string_to_list
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
    # http namespace
    #     the namespace is for config parameters the http modules
    #--------------------------------------------------------------------------
    required_config.namespace('http')
    required_config.http.namespace('correlations')
    required_config.http.correlations.add_option(
        'base_url',
        doc='Base URL where correlations text files are',
        default='https://crash-analysis.mozilla.com/crash_analysis/',
    )
    required_config.http.correlations.add_option(
        'save_download',
        doc='Whether files downloaded for correlations should be '
            'temporary stored on disk',
        default=True,
    )
    required_config.http.correlations.add_option(
        'save_seconds',
        doc='Number of seconds that the downloaded .txt file is stored '
            'in a temporary place',
        default=60 * 10,
    )
    required_config.http.correlations.add_option(
        'save_root',
        doc='Directory where the temporary downloads are stored '
            '(if left empty will become the systems tmp directory)',
        default='',
    )

    #--------------------------------------------------------------------------
    # sentry namespace
    #     the namespace is for Sentry error capturing with Raven
    #--------------------------------------------------------------------------
    required_config.namespace('sentry')
    required_config.sentry.add_option(
        'dsn',
        doc='DSN for Sentry via raven',
        default='',
        reference_value_from='secrets.sentry',
    )

    #--------------------------------------------------------------------------
    # introspection namespace
    #     the namespace for things related to running middleware
    #--------------------------------------------------------------------------
    required_config.namespace('introspection')
    required_config.introspection.add_option(
        'implementation_class',
        default='socorro.middleware.middleware_app.ImplementationWrapper',
        from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    @staticmethod
    def get_application_defaults():
        return {
            "web_server.port": 8883,
        }

    #--------------------------------------------------------------------------
    def main(self):
        # modwsgi requires a module level name 'application'
        global application

        # 1 turn these names of classes into real references to classes
        def lookup(file_and_class):
            file_name, class_name = file_and_class.rsplit('.', 1)
            overrides = dict(self.config.implementations.service_overrides)
            _list = self.config.implementations.implementation_list
            for prefix, base_module_path in _list:
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

        # This list will hold the collection of url/service-implementations.
        # It is populated in the for loop a few lines lower in this file.
        # This list is used in the 'wrap' function so that all services have
        # place to lookup dependent services.

        all_services_mapping = {}

        implementation_class = self.config.introspection.implementation_class

        # 2 wrap each service class with the ImplementationWrapper class
        def wrap(cls, file_and_class):
            return type(
                cls.__name__,
                (implementation_class,),
                {
                    'cls': cls,
                    'file_and_class': file_and_class,
                    # give lookup access of dependent services to all services
                    'all_services': all_services_mapping,
                    'config': self.config,
                }
            )

        services_list = []
        # populate the 'services_list' with the tuples that will define the
        # urls and services offered by the middleware.
        for url, impl_class in self.SERVICES_LIST:
            impl_instance = lookup(impl_class)
            wrapped_impl = wrap(impl_instance, impl_class)
            services_list.append((url, wrapped_impl))
            all_services_mapping[impl_instance.__name__] = wrapped_impl

        self.web_server = self.config.web_server.wsgi_server_class(
            self.config,  # needs the whole config not the local namespace
            services_list
        )

        # for modwsgi the 'run' method returns the wsgi function that
        # will use.  For other webservers, the 'run' method actually starts
        # the standalone web server.
        application = self.web_server.run()


class ImplementationWrapper(JsonWebServiceBase):

    def GET(self, *args, **kwargs):
        # prepare parameters
        params = self._get_query_string_params()
        params.update(kwargs)

        # override implementation class if needed
        if params.get('_force_api_impl'):
            impl_code = params['_force_api_impl']

            file_name, class_name = self.file_and_class.rsplit('.', 1)
            implementations = dict(
                self.config.implementations.implementation_list
            )

            try:
                base_module_path = implementations[impl_code]
            except KeyError:
                raise BadRequest(
                    'Implementation code "%s" does not exist' % impl_code
                )

            try:
                module = __import__(
                    '%s.%s' % (base_module_path, file_name),
                    globals(),
                    locals(),
                    [class_name]
                )
            except ImportError:
                raise BadRequest(
                    "Unable to import %s.%s.%s (implementation code is %s)" %
                    (base_module_path, file_name, class_name, impl_code)
                )
            instance = getattr(module, class_name)(
                config=self.config,
                all_services=self.all_services
            )
        else:
            instance = self.cls(
                config=self.config,
                all_services=self.all_services
            )

        # find the method to call
        default_method = kwargs.pop('default_method', 'get')
        if default_method not in ('get', 'post', 'put', 'delete'):
            raise ValueError('%s not a recognized method' % default_method)
        method_name = default_method
        if len(args) > 1:
            method_name = args[0]
        try:
            method = getattr(instance, method_name)
        except AttributeError:
            try:
                if (method_name == 'post' and
                   getattr(instance, 'create', None)):
                    # use the `create` alias
                    method = instance.create
                elif (method_name == 'put' and
                      getattr(instance, 'update', None)):
                    # use the `update` alias
                    method = instance.update
                elif (default_method == 'post' and
                      getattr(instance, 'create_%s' % method_name, None)):
                    # use `create_<method>`
                    method = getattr(instance, 'create_%s' % method_name)
                elif (default_method == 'put' and
                      getattr(instance, 'update_%s' % method_name, None)):
                    # use `update_<method>`
                    method = getattr(instance, 'update_%s' % method_name)
                else:
                    if method_name.startswith(default_method):
                        raise AttributeError
                    method = getattr(
                        instance,
                        '%s_%s' % (default_method, method_name)
                    )
            except AttributeError:
                self.config.logger.warning(
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
            dumped = ujson.dumps(result)
            web.header('Content-Length', len(dumped))
            return dumped

        except (MissingArgumentError, BadArgumentError), msg:
            raise BadRequest({
                'error': {
                    'message': str(msg)
                }
            })
        except ResourceNotFound, msg:
            raise NotFound({
                'error': {
                    'message': str(msg)
                }
            })
        except ResourceUnavailable, msg:
            raise Timeout({
                'error': {
                    'message': str(msg)
                }
            })
        except Exception, msg:
            if self.config.sentry and self.config.sentry.dsn:
                client = raven.Client(dsn=self.config.sentry.dsn)
                identifier = client.get_ident(client.captureException())
                self.config.logger.info(
                    'Error captured in Sentry. Reference: %s' % identifier
                )
            raise

    def POST(self, *args, **kwargs):
        # this is necessary in case some other method (e.g PUT) overrides
        # this method.
        default_method = kwargs.pop('default_method', 'post')
        params = self._get_web_input_params()
        data = web.data()
        if data:
            # If you post a payload as the body it gets picked up by
            # webapi in `web.data()` as a string.
            # It will also, rather annoyingly, make this data a key
            # in the output of `web.input()` which we also rely on.
            # So, in that case try to remove it as a key.
            try:
                params.pop(data)
            except KeyError:
                pass
            params['data'] = data
        return self.GET(default_method=default_method, *args, **params)

    def PUT(self, *args, **kwargs):
        return self.POST(default_method='put', *args, **kwargs)

    def DELETE(self, *args, **kwargs):
        params = self._get_web_input_params()
        return self.GET(default_method='delete', *args, **params)

    def _get_query_string_params(self):
        params = {}
        query_string = web.ctx.query[1:]

        for key, values in cgi.parse_qs(query_string).items():
            if len(values) == 1:
                values = values[0]
            params[key] = values

        return params

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


class MeasuringImplementationWrapper(ImplementationWrapper):
    """This class does nothing differently than its parent class except it
    measures how long it takes to generated the data for every GET request.

    This timing is just to get and collect the data. It excludes the time
    to parse the request and to serialize to JSON.

    Use it only for development purposes to give yourself a feel for how
    much time is spent on gathering different pieces of data.
    """

    def GET(self, *args, **kwargs):
        t0 = time.time()
        result = (
            super(MeasuringImplementationWrapper, self)
            .GET(*args, **kwargs)
        )
        t1 = time.time()
        self.config.logger.info(
            'measuringmiddleware:%.2f\t%s\t%s' % (
                1000 * (t1 - t0),
                web.ctx.path,
                web.ctx.query
            )
        )
        return result


if __name__ == '__main__':
    main(MiddlewareApp)
