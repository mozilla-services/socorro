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
there is a PostgreSQL submodule, an ElasticSearch submodule and a HBase
submodule.

You will also find some common code among external resources in socorro.lib.

Class hierarchy
---------------

.. image:: images/middleware-hierarchy.png

Create the service
------------------

First create a new file for your service in ``socorro/middleware/`` and call it
``nameofservice_service.py``. This is a convention for the next version of our
config manager. Then create a class inside as follow::

    import logging

    from socorro.middleware.service import DataAPIService

    logger = logging.getLogger("webapi")


    class MyService(DataAPIService):

        default_service_order = [
            "socorro.external.myresource",
            "socorro.external.postgresql"
            "socorro.external.elasticsearch"
        ]
        service_name = "myservice"
        uri = "/myservice/(.*)"

        def __init__(self, config):
            super(MyService, self).__init__(config)
            logger.debug('MyService service __init__')

        def get(self, *args):
            # Parse parameters
            params = self.parse_query_string(args[0])

            module = self.get_module(params)
            impl = module.MyService(config=self.context)

            return impl.mymethod(**params)

``uri`` is the URL pattern you want to match. It is a regular expression, and
the content of each part (``(.*)``) will be in ``args``.

``service_name`` is the name of your service, and will be used to find the
corresponding implementation resource. It has to match the filename of the
module you need.

``default_service_order`` is a configuration variable containing prefered
implementation resources in case the global configuration value does not
contain the needed module.

If you want to add mandatory parameters, modify the URI and values will be
passed in ``args``.

Use external resources
----------------------

The ``socorro.external`` contains everything related to outer resources like
databases. Each submodule has a base class and classes for specific
functionalities. If the function you need for your service is not already in
there, you create a new file and a new class to implement it. To do so,
follow this pattern::

    from socorro.external.myresource.base import MyResourceBase


    class MyModule(MyResourceBase):

        def __init__(self, *args, **kwargs):
            super(MyModule, self).__init__(*args, **kwargs)

        def mymethod(self, **kwargs):
            do_stuff()
            return my_json_result

Configuration
-------------

Finally add your service to the list of running services in
scripts/config/webapiconfig.py.dist as follow::

    import socorro.middleware.search_service as search
    import socorro.middleware.myservice_service as myservice # add

    servicesList = cm.Option()
    servicesList.doc = 'a python list of classes to offer as services'
    servicesList.default = [myservice.MyService, search.Search, (...)] # add

Then restart Apache and you should be good to go! If you're using a Vagrant VM,
you can hit the middleware directly by calling
http://socorro-api/bapi/myservice/params/.

And then?
---------

Once you are done creating your service in the middleware, you might want to
use it in the WebApp. If so, have a look at :ref:`ui-chapter`.

You might also want to document it. We are keeping track of all existing
services' documentation in our :ref:`middleware-chapter` page. Please add
yours!
