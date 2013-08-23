.. index:: addaservice

.. _addaservice-chapter:

Add a service to the Middleware
===============================

Architecture overview
---------------------

The middleware is a simple REST API providing JSON data depending on the URL
that is called. It is made of a list of services, each one binding a certain
URL with parameters. Documentation for each service is available in the
:ref:`middleware-chapter` page.

Those services are not containing any code, but are only interfaces. They are
using other resources from the external module. That external module is
composed of one submodule for each external resource we are using. For example,
there is a PostgreSQL submodule, an elasticsearch submodule and an HBase
submodule.

You will also find some common code among external resources in
``socorro.lib``.

The "Middleware" in Socorro is divided into two separate modules.
``socorro/middleware/middleware_app.py`` is the file that contains the actual
service, the class that will receive HTTP requests and return the right data.
However, services do not do any kind of computation, they only find the right
implementation class and call it.

Implementations of services are found in ``socorro/external/``. They are
separated in submodules, one for each external resource that we use. For
example, in ``socorro/external/postgresql/`` you will find everything that is
related to data stored in PostgreSQL: SQL queries mainly, but also arguments
sanitizing and data formatting.


Naming conventions
------------------

We have decided upon a simple convention when naming API endpoints::

    url: /(resource)/(aggregation)/(parameters)/
    class: Resource
    method: get_aggregation

For example, you want your service to return crashes aggregated by comments,
your service will thus have the URL ``/crashes/comments``. Then your
implementation class will be named ``Crashes`` and it will have a method
called ``get_comments``. If you want to simply return products, use the URL
``/products``, name your implementation ``Products`` and have a ``get`` method.
The second part of the url, the method, is optional. If omitted, the
implementation class is expected to have a method that matches the HTTP method
used. For example ``GET /android-devices/``, when configured to the
implementation class ``AndroidDevices`` will thus attempt to execute the
``AndroidDevices.get()`` method. Similarly, if you did
``POST /android-devices/`` it will execute ``AndroidDevices.post()``.

That's the theory anyway. If your service just doesn't fit in that model, feel
free to make up a URL that looks like the other services. Simple rules to
follow: separate words with underscores in URLs and file names, use CamelCase
in class names.

REST APIs have 4 major actions, which are GET, POST, PUT and DELETE. When
building your implementation, you will want to have methods that will match
the actions that you support. The convention we decided upon is as follow::

    GET /products -> get
    POST /products -> create
    PUT /products -> update
    DELETE /products -> delete

If your service has an aggregation, then you will need to add that aggregation
to the method name, separated by an underscore. For example::

    GET /crashes/comments -> get_comments
    POST /crashes/comments -> create_comments
    PUT /crashes/comments -> update_comments
    DELETE /crashes/comments -> delete_comments


Implement your service
----------------------

The ``socorro.external`` contains everything related to outer resources like
databases. Each submodule has a base class and classes for specific
functionalities. If the function you need for your service is not already in
there, create a new file and a new class to implement it.

So, let's say you want to add a service that returns the signature of a crash
based on that crash's ID. The service's URL will be quite simple: ``/crash``.
You want to implement that service with PostgreSQL, so you will need to create
a new file in ``socorro/external/postgresql`` that will be named ``crash.py``.
Then in that file, you will create a class called ``Crash`` and give a ``get``
method that will contain all your business logic. For example::

    # file socorro/external/postgresql/crash.py

    from socorro.external import MissingOrBadArgumentError
    from socorro.external.postgresql.base import PostgreSQLBase
    from socorro.lib import external_common


    class Crash(PostgreSQLBase):
        def get(self, **kwargs):
            '''Return the signature of a crash report from its UUID. '''
            # Define the parameters that this service accepts, their default
            # value and their type, and then parse the arguments that were passed.
            filters = [
                ('uuid', None, 'str'),
            ]
            params = external_common.parse_arguments(filters, kwargs)

            if not params.uuid:
                raise MissingOrBadArgumentError(
                    'Mandatory parameter "uuid" is missing or empty'
                )

            sql = '''/* socorro.external.postgresql.crash.Crash.get */
                SELECT signature
                FROM reports
                WHERE uuid=%(uuid)s
            '''

            error_message = 'Failed to retrieve crash data from PostgreSQL'
            results = self.query(sql, params, error_message=error_message)

            return {
                'signature': results[0][0],
            }

.. sidebar:: Special values and JSON

    ``json.dumps`` doesn't accept Python dates and ``Decimal``. If you have
    one of those in your return values, you will want to cast them manually
    before returning. For example, use ``datetimeutil.date_to_string()``
    to turn a date into a string, and ``float()`` for ``Decimal`` (or for
    greater accuracy, convert your ``Decimal`` instance to a string with the
    exact number of significant figures that you need).

The return value should be anything that ``json.dumps`` can parse. Most of
the time you will want to return a dictionary.

Here is the documentation of the ``external_common.parse_arguments`` function::

    Return a dict of parameters.

    Take a list of filters and for each try to get the corresponding
    value in arguments or a default value. Then check that value's type.

    Example:
        filters = [
            ("param1", "default", ["list", "str"]),
            ("param2", None, "int"),
            ("param3", ["list", "of", 4, "values"], ["list", "str"])
        ]
        arguments = {
            "param1": "value1",
            "unknown": 12345
        }
        =>
        {
            "param1": ["value1"],
            "param2": 0,
            "param3": ["list", "of", "4", "values"]
        }

And here is an example of how to use this::

    class Products(PostgreSQLBase):
        def versions_info(self, **kwargs):
            # Parse arguments
            filters = [
                ("product", "Firefox", "str"),
                ("versions", None, ["list", "str"])
            ]
            params = external_common.parse_arguments(filters, kwargs)

            params.product # "Firefox" by default or a string
            params.versions # [] by default or a list of strings


Unit testing and integration testing
------------------------------------

It is essential to test your new service, and you can do so in several ways.
If you have written business logic that doesn't deal with any external
resource, such as a database, you can use a unit test. However, most of the
time middleware services return values that come from a database, and you
want to test that the database behaves as expected.

Here is an example of an integration test file for a PostgreSQL service
(testing the service that was created in the previous section)::

    from nose.plugins.attrib import attr

    from socorro.external import MissingOrBadArgumentError
    from socorro.external.postgresql.crash import Crash
    from unittestbase import PostgreSQLTestCase


    @attr(integration='postgres')  # for nosetests
    class IntegrationTestCrash(PostgreSQLTestCase):
        '''Test socorro.external.postgresql.crash.Crash class. '''

        def setUp(self):
            '''Set up this test class by populating the reports table with fake
            data. '''
            super(IntegrationTestCrash, self).setUp()

            cursor = self.connection.cursor()

            # Insert data
            cursor.execute('''
                INSERT INTO reports
                (id, signature)
                VALUES
                (
                    1,
                    'fake_signature_1'
                ),
                (
                    2,
                    'fake_signature_2'
                );
            ''')

            self.connection.commit()

        def tearDown(self):
            '''Clean up the database, delete tables and functions. '''
            cursor = self.connection.cursor()
            cursor.execute('TRUNCATE reports CASCADE')
            self.connection.commit()
            super(IntegrationTestCrash, self).tearDown()

        def test_get(self):
            api = Crash(config=self.config)

            # Test 1: test something
            params = {
                'uuid': 1
            }
            res = api.get(**params)
            res_expected = {
                'signature': 'fake_signature_1'
            }
            self.assertEqual(res, res_expected)

            # Test 2: test something else
            params = {
                'uuid': 1
            }
            res = api.get(**params)
            res_expected = {
                'signature': 'fake_signature_3'
            }
            self.assertEqual(res, res_expected)

            # Test 3: test the expections
            self.assertRaises(
                MissingOrBadArgumentError,
                api.get()
            )

See the :ref:`unittesting-chapter` page for more information on how to run
tests.


Expose your service
-------------------

We currently support 2 different middlewares. The current one is based on a lot
of files in ``socorro.middleware``, and the new one is using ``configman``,
our new configuration manager. Sadly, at the moment you will need to expose
your new service in both systems, until we get rid of the current middleware.

With the new configman-middleware
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The way it works overall is simple: ``socorro/middleware/middleware_app.py``
has a list (called ``SERVICES_LIST``) of tuples, each tuple being composed
of 2 elements:

1.  the URL that you want to expose (e.g. ``/my_service/(foo|bar|baz)``);
2.  a dot delimited notation that describes the implementation to use
    (e.g. ``services.MyService``).

The middleware also has a list of implementations, that it will go through
when looking for a service implementation. By default, the first one is
``postgresql`` as this is the most common one. So, if your service's
implementation is ``services.MyService``, the middleware will try to first
import ``socorro.external.postgresql.services.MyService``, and if that fails
it will try with other implementations.

So, on to exposing your service...

In ``socorro/middleware/middleware_app.py``, add a line to ``SERVICES_LIST``
with the details of your service: its URL and its implementation class. For
example::

    SERVICES_LIST = (
        (r'/bugs/(.*)', 'bugs.Bugs'),
        (r'/crash_data/(.*)', 'crash_data.CrashData'),
        # Add this line
        (r'/crash/(.*)', 'crash.Crash'),
    )

That's all you need to do to make it work! However, adding a unit test for
this new service might be a good thing. Those are located in
``socorro/unittest/middleware/test_middleware_app.py``.

If you want your service to be using a different service than the default one
(usually ``postgresql``), you can add it to the list of ``service_overrides``
in the configuration. If you want to write a class that doesn’t belong to any
of the types of implementations listed in the default configuration for
``implementation_list`` the best thing to do is to simply add it there.

To test your service, start the middleware and try to access the new URL::

    $ curl http://domain/crash/uuid/xxx-xxx-xxx/

With the old middleware
^^^^^^^^^^^^^^^^^^^^^^^

First create a new file for your service in ``socorro/middleware/`` and call it
``nameofservice_service.py``. Then create a class inside as follow::

    import logging

    from socorro.middleware.service import DataAPIService

    logger = logging.getLogger("webapi")


    class Crash(DataAPIService):

        service_name = "crash" # Name of the submodule to look for in external
        uri = "/crash/(.*)" # URL of the service

        def __init__(self, config):
            super(Crash, self).__init__(config)
            logger.debug('Crash service __init__')

        def get(self, *args):
            # Parse parameters of the URL
            params = self.parse_query_string(args[0])

            # Find the implementation module in external depending on the configuration
            module = self.get_module(params)

            # Instantiate the implementation class
            impl = module.Crash(config=self.context)

            # Call and return the result of the implementation method
            return impl.get(**params)

``uri`` is the URL pattern you want to match. It is a regular expression, and
the content of each part (``(.*)``) will be in ``args``.

``service_name`` will be used to find the corresponding implementation
resource. It has to match the filename of the module you need.

If you want to add mandatory parameters, modify the URI and values will be
passed in ``args``.

Finally add your service to the list of running services in
scripts/config/webapiconfig.py.dist as follow::

    import socorro.middleware.search_service as search
    import socorro.middleware.myservice_service as myservice # add

    servicesList = cm.Option()
    servicesList.doc = 'a python list of classes to offer as services'
    servicesList.default = [myservice.MyService, search.Search, (...)] # add

You can also add a config key for the implementation of your service. If you
don't, your service will use the default config key
(``serviceImplementationModule``). To add a specific configuration key::

    # MyService service config
    myserviceImplementationModule = cm.Option()
    myserviceImplementationModule.doc = "String, name of the module myservice uses."
    myserviceImplementationModule.default = 'socorro.external.elasticsearch' # for example

Then restart Apache and you should be good to go! If you're using a Vagrant VM,
you can hit the middleware directly by calling
http://socorro-api/bpapi/myservice/params/.


And then?
---------

Once you are done creating your service in the middleware, you might want to
use it in the WebApp. You might also want to document it. We are keeping track
of all existing services' documentation in our :ref:`middleware-chapter` page.
Please add yours!


Ensuring good style
-------------------

To ensure that the Python code you wrote passes PEP8 you need to run check.py.
To do this your first step is to install it. From the terminal run::

    pip install -e git://github.com/jbalogh/check.git#egg=check

P.S. You may need to sudo the command above

Once installed, run the following::

    check.py /path/to/your/file
