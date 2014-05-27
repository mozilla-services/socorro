#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""implementation of the Socorro data service"""

# This app can be invoked like this:
#     .../socorro/middleware/middleware_app.py --help
# replace the ".../" with something that makes sense for your environment
# set both socorro and configman in your PYTHONPATH

import cgi
import json
import re
import web
from socorro.app.generic_app import App, main
from socorro.external import (
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
from configman import Namespace, RequiredConfig
from configman.converters import class_converter


#------------------------------------------------------------------------------
def classes_in_namespaces_converter(
    attr_name_for_resource_class='crashstorage_class',
    instantiate_classes=False
):
    """take a comma delimited  list of namespaces & class names, convert each
    class name into an actual class as an option within the named namespace.
    This function creates a closure over a new function.  That new function,
    in turn creates a class derived from RequiredConfig.  The inner function,
    'class_list_converter', populates the InnerClassList with a Namespace for
    each of the classes in the class list.  In addition, it puts the each class
    itself into the subordinate Namespace.  The requirement discovery mechanism
    of configman then reads the InnerClassList's requried config, pulling in
    the namespaces and associated classes within.

    For example, if we have a class list like this: "alf:Alpha, bet:Beta",
    then this converter will add the following Namespaces and options to the
    configuration:

        "alf" - the subordinate Namespace for Alpha
        "alf.alf_class" - the option containing the class Alpha itself
        "bet" - the subordinate Namespace for Beta
        "bet.bet_class" - the option containing the class Beta itself

    Optionally, the 'class_list_converter' inner function can embue the
    InnerClassList's subordinate namespaces with aggregates that will
    instantiate classes from the class list.  This is a convenience to the
    programmer who would otherwise have to know ahead of time what the
    namespace names were so that the classes could be instantiated within the
    context of the correct namespace.  Remember the user could completely
    change the list of classes at run time, so prediction could be difficult.

        "alf" - the subordinate Namespace for Alpha
        "alf.alf_class" - the option containing the class Alpha itself
        "alf.cls_instance" - an instance of the class Alpha
        "bet" - the subordinate Namespace for Beta
        "bet.bet_class" - the option containing the class Beta itself
        "bet.cls_instance" - an instance of the class Beta

    parameters:
        class_option_name - the name to be used for the class option within
                            the nested namespace.  By default, it will choose:
                            "cls1.cls", "cls2.cls", etc.
        instantiate_classes - a boolean to determine if there should be an
                              aggregator added to each namespace that
                              instantiates each class.  If True, then each
                              Namespace will contain elements for the class, as
                              well as an aggregator that will instantiate the
                              class.
                              """

    #--------------------------------------------------------------------------
    def class_list_converter(class_list_str):
        """This function becomes the actual converter used by configman to
        take a string and convert it into the nested sequence of Namespaces,
        one for each class in the list.  It does this by creating a proxy
        class stuffed with its own 'required_config' that's dynamically
        generated."""
        if isinstance(class_list_str, basestring):
            temp_list = [x.strip() for x in class_list_str.split(',')]
            if temp_list == ['']:
                temp_list = []
            # now we should have a list of ":" delimited namespace/class pairs
            class_list = []
            for a_pair in temp_list:
                if a_pair:
                    namespace_name, class_name = a_pair.split(':')
                    namespace_name = namespace_name.strip()
                    class_name = class_name.strip()
                    class_list.append((namespace_name, class_name))
        else:
            raise TypeError('must be derivative of a basestring')

        #======================================================================
        class InnerClassList(RequiredConfig):
            """This nested class is a proxy list for the classes.  It collects
            all the config requirements for the listed classes and places them
            each into their own Namespace.
            """
            # we're dynamically creating a class here.  The following block of
            # code is actually adding class level attributes to this new class
            required_config = Namespace()  # 1st requirement for configman
            subordinate_namespace_names = []  # to help the programmer know
                                              # what Namespaces we added
            # save the class's option name for the future
            class_option_name = attr_name_for_resource_class
            original_class_list_str = class_list_str
            # for each class in the class list
            for namespace_name, a_class in (class_list):
                # figure out the Namespace name
                subordinate_namespace_names.append(namespace_name)
                # create the new Namespace
                required_config[namespace_name] = Namespace()
                # add the option for the class itself
                required_config[namespace_name].add_option(
                    attr_name_for_resource_class,
                    #doc=a_class.__doc__  # not helpful if too verbose
                    default=a_class,
                    from_string_converter=class_converter
                )
                if instantiate_classes:
                    # add an aggregator to instantiate the class
                    required_config[namespace_name].add_aggregation(
                        "%s_instance" % attr_name_for_resource_class,
                        lambda c, lc, a: lc[attr_name_for_resource_class](lc)
                    )

            @classmethod
            def to_str(cls):
                """this method takes this inner class object and turns it back
                into the original string of classnames.  This is used
                primarily as for the output of the 'help' option"""
                return cls.original_class_list_str

        return InnerClassList  # result of class_list_converter
    return class_list_converter  # result of classes_in_namespaces_converter


#------------------------------------------------------------------------------
# Here's the list of URIs mapping to classes and the files they belong to.
# The final lookup depends on the `implementation_list` option inside the app.
SERVICES_LIST = (
    (r'/bugs/(.*)', 'bugs.Bugs'),
    (r'/crash_data/(.*)', 'crash_data.CrashData'),
    (r'/crash/(.*)', 'crash.Crash'),
    (r'/crashes/'
     r'(comments|count_by_day|daily|frequency|paireduuid|signatures|'
     r'signature_history|exploitability|adu_by_signature)/(.*)',
     'crashes.Crashes'),
    (r'/extensions/(.*)', 'extensions.Extensions'),
    (r'/field/(.*)', 'field.Field'),
    (r'/crashtrends/(.*)', 'crash_trends.CrashTrends'),
    (r'/job/(.*)', 'job.Job'),
    (r'/platforms/(.*)', 'platforms.Platforms'),
    (r'/priorityjobs/(.*)', 'priorityjobs.Priorityjobs'),
    (r'/products/builds/(.*)', 'products_builds.ProductsBuilds'),
    (r'/products/(.*)', 'products.Products'),
    (r'/query/', 'query.Query'),
    (r'/releases/(featured)/(.*)', 'releases.Releases'),
    (r'/signatureurls/(.*)', 'signature_urls.SignatureURLs'),
    (r'/signaturesummary/(.*)', 'signature_summary.SignatureSummary'),
    (r'/search/(signatures|crashes)/(.*)', 'search.Search'),
    (r'/supersearch/(field|fields)/(.*)', 'supersearch.SuperSearch'),
    (r'/supersearch/(.*)', 'supersearch.SuperSearch'),
    (r'/server_status/(.*)', 'server_status.ServerStatus'),
    (r'/report/(list)/(.*)', 'report.Report'),
    (r'/util/(versions_info)/(.*)', 'util.Util'),
    (r'/crontabber_state/(.*)', 'crontabber_state.CrontabberState'),
    (r'/correlations/signatures/(.*)', 'correlations.CorrelationsSignatures'),
    (r'/correlations/(.*)', 'correlations.Correlations'),
    (r'/skiplist/(.*)', 'skiplist.SkipList'),
    (r'/backfill/(.*)', 'backfill.Backfill'),
    (r'/suspicious/(.*)', 'suspicious.SuspiciousCrashSignatures'),
    (r'/laglog/(.*)', 'laglog.LagLog'),
    (r'/gccrashes/(.*)', 'gccrashes.GCCrashes'),
    (r'/graphics_devices/(.*)', 'graphics_devices.GraphicsDevices'),
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
        default='database:socorro.external.postgresql, '
                #'primary_storage:socorro.external.hb, '
                # conisder changing "webapi" to "search"
                'webapi:socorro.external.elasticsearch, '
                'primary_storage:socorro.external.fs, '
                # conisder changing "webapi" to "analysis"
                'http:socorro.external.http, '
                'queuing:socorro.external.rabbitmq',
        from_string_converter=items_list_decode,
        to_string_converter=items_list_encode
    )

    required_config.implementations.add_option(
        'service_overrides',
        doc='comma separated list of class overrides, e.g `Crashes: hbase`',
        default='CrashData: primary_storage, '
                'Correlations: http, '
                'CorrelationsSignatures: http, '
                'SuperSearch: webapi, '
                'Priorityjobs: queuing, '
                'Query: webapi',
        from_string_converter=items_list_decode,
        to_string_converter=items_list_encode
    )

    required_config.add_option(
        'service_classes',
        doc='a list of namespace:class associations for classes that offer '
            ' implementations of services',
        # these classes bring the basic resource configuration parameters into
        # the middleware configuration.  Each resource listed in this section
        # will have a namespace in the middleware config root correspondng to
        # key given in the entry here. Each of the web services implemented
        # by that resource will look to that namespace entry for configuration
        # info. This entry makes that happen by calling the local
        # classes_in_namespaces_converter
        # role: database - for any service that want to access a database with
        #                  a database connection.  Offering a transaction
        #                  manager would sure be nice.
        # role: primary_storage - services in this role always want a crash-
        #                         storage instance rather than a bare
        #                         to some resource.
        # role: queuing - the services in this category want bare connections
        #                 to their resources
        default="""
database: socorro.external.postgresql.crashstorage.PostgreSQLCrashStorage,
primary_storage: socorro.external.fs.crashstorage.FSLegacyRadixTreeStorage,
queuing: socorro.external.rabbitmq.crashstorage.RabbitMQCrashStorage""",
        from_string_converter=classes_in_namespaces_converter()
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
        'elasticsearch_urls',
        default=['http://localhost:9200'],
        doc='the urls to the elasticsearch instances',
        from_string_converter=string_to_list,
        reference_value_from='resource.elasticsearch',
    )
    required_config.webapi.add_option(
        'elasticsearch_index',
        default='socorro%Y%W',
        doc='an index format to pull crashes from elasticsearch '
            "(use datetime's strftime format to have "
            'daily, weekly or monthly indexes)',
        reference_value_from='resource.elasticsearch',
    )
    required_config.webapi.add_option(
        'elasticsearch_doctype',
        default='crash_reports',
        doc='the default doctype to use in elasticsearch',
        reference_value_from='resource.elasticsearch',
    )
    required_config.webapi.add_option(
        'elasticsearch_timeout',
        default=30,
        doc='the time in seconds before a query to elasticsearch fails',
        reference_value_from='resource.elasticsearch',
    )
    required_config.webapi.add_option(
        'elasticsearch_timeout_extended',
        default=120,
        doc='the time in seconds before a query to elasticsearch fails in '
            'restricted sections',
        reference_value_from='resource.elasticsearch',
    )
    required_config.webapi.add_option(
        'facets_max_number',
        default=50,
        doc='the maximum number of results a facet will return in search'
    )
    required_config.webapi.add_option(
        'searchMaxNumberOfDistinctSignatures',
        default=1000,
        doc='Integer containing the maximum allowed number of distinct '
            'signatures the system should retrieve. Used mainly for '
            'performances in ElasticSearch'
    )
    required_config.webapi.add_option(
        'search_default_date_range',
        default=7,  # in days
        doc='the default date range for searches, in days'
    )
    required_config.webapi.add_option(
        'search_maximum_date_range',
        default=365,  # in days
        doc='the maximum date range for searches, in days'
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
    # laglog namespace
    #     the namespace for the replica lag log
    #--------------------------------------------------------------------------
    required_config.namespace('laglog')
    required_config.laglog.add_option(
        'max_bytes_warning',
        default=16 * 1024 * 1024,
        doc="Number of bytes that warrents a warning"
    )
    required_config.laglog.add_option(
        'max_bytes_critical',
        default=32 * 1024 * 1024,
        doc="Number of bytes that warrents a critial"
    )

    # because the socorro.webapi.servers classes bring up their own default
    # configurations like port number, the only way to override the default
    # is like this:
    from socorro.webapi.servers import StandAloneServer
    StandAloneServer.required_config.port.set_default(8883, force=True)

    #--------------------------------------------------------------------------
    def lookup(self, file_and_class):
        #turn these names of classes into real references to classes
        file_name, class_name = file_and_class.rsplit('.', 1)
        try:
            if class_name in self.overrides:
                target_role = self.overrides[class_name]
                base_module_path = self.implementations[target_role]
            else:
                base_module_path = (
                    self.config.implementations.implementation_list[0][1]
                )
                target_role = (
                    self.config.implementations.implementation_list[0][0]
                )
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
            impl_class = getattr(module, class_name)

            class RoleImbuedImplClass(impl_class):
                role = target_role
                class_key = "%s_class" % target_role
            return RoleImbuedImplClass
        except (KeyError, IndexError), x:
            raise ImplementationConfigurationError(file_and_class)

    #--------------------------------------------------------------------------
    def main(self):
        # Apache modwsgi requireds a module level name 'application'
        global application

        self.overrides = dict(self.config.implementations.service_overrides)
        self.implementations = dict(
            self.config.implementations.implementation_list
        )

        all_services_mapping = {}

        def wrap(cls, file_and_class):
            return type(
                cls.__name__,
                (ImplementationWrapper,),
                {
                    'cls': cls,
                    'file_and_class': file_and_class,
                    # give lookup access of dependent services to all services
                    'all_services': all_services_mapping,
                }
            )

        services_list = []
        # populate the 'services_list' with the tuples that will define the
        # urls and services offered by the middleware.
        for url, impl_class in SERVICES_LIST:
            impl_instance = self.lookup(impl_class)
            wrapped_impl = wrap(impl_instance, impl_class)
            services_list.append((url, wrapped_impl))
            all_services_mapping[impl_instance.__name__] = wrapped_impl

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
        # prepare parameters
        params = self._get_query_string_params()
        params.update(kwargs)

        # override implementation class if needed
        if params.get('_force_api_impl'):
            impl_code = params['_force_api_impl']

            file_name, class_name = self.file_and_class.rsplit('.', 1)
            implementations = dict(
                self.context.implementations.implementation_list
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
                config=self.context,
                all_services=self.all_services
            )
        else:
            instance = self.cls(
                config=self.context,
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
            if self.context.sentry and self.context.sentry.dsn:
                client = raven.Client(dsn=self.context.sentry.dsn)
                identifier = client.get_ident(client.captureException())
                self.context.logger.info(
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


if __name__ == '__main__':
    main(MiddlewareApp)
