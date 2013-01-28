.. index:: addingmiddleware

.. _addingmiddleware-chapter:

Adding new Middleware Services
==============================

Your first and best source for this is to read existing code and
existing middleware services for "inspiration". Let's walk through
that a bit.

The first thing you need to do is to edit
``socorro/middleware/middleware_app.py`` and add your URL to the tuple
called ``SERVICES_LIST``. Each entry is a tuple of two things. It works like this::

1. The URL that you want to expose. E.g. ``/my/special/(foo|bar|baz)``

2. A dot delimited notation that describes ``modulename.ClassName``.

So, if you have a file called
``socorro/external/postgresql/special.py`` that contains a class
called ``MySpecial`` it would become ``special.MySpecial``.

How does it know that the module is in
``socorro/external/postgresql/``? It doesn't. But that's one of the
default suggestions where to look for modules. This is thanks to a
configman based option called ``implementation_list``.

What the middleware_app does is that it loops over each entry in
``implementation_list`` and tries each one as a potential start to go
with your ``special.MySpecial`` until it manages to import it.

If it fails to find your module and class anywhere, an
``ImplementationConfigurationError`` error will be raised.

Writing the class
-----------------

Which base class you use for your new middleware service does not
matter. You might obviously save yourself a lot of pain and time by
using one of the existing base classes that some of the other services
use. For example ``socorro.external.postgresql.base.PostgreSQLBase``.

What is important is that your class has one of the following methods:

 * ``get``

 * ``post``

 * ``put``

 * ``create`` (alias for ``post``)

 * ``update`` (alias for ``put``)

As you can guess the ``post`` and ``create`` is for ``POST`` requests
and equally ``put`` and ``update`` is exclusively for ``PUT`` requests.
Other types of request methods such as ``DELETE`` or ``OPTIONS`` would
need to extend middleware_app to work.

But there's more. Where appropriate, if your regular expression used
for the URL contains more than one variable. For example like this:
``/my/special/(foo|bar|baz)/(.*?)/`` then your class can have methods
like ``get_foo`` or ``get_bar`` or ``update_baz`` etc. Basically
anything that can be combined and it will be found. For example, this
would work if you have a method on your class called ``create_bar``::

    $ curl -X POST http://domain/my/special/bar/SomeValue

And it would effectively do this to your class::

    instance = MySpecial()
    result = instance.create_bar('SomeValue')

Writing the output
------------------

Your service class and its methods just need to return some data
structure that will work with ``json.dumps()``. For example a simple
``dict``. The middleware_app
will take care of all the formatting and headers.


Exceptional exceptions
----------------------

If you want to write a class that doesn't belong to any of types of
implementations listed in the default configuration for
``implementation_list`` the best thing to do is to simply add it.

Because the list of services (and their respective URL) is hardcoded
in ``middleware_app.py`` you're going to have to edit it anyway. So
you can add another entry for that list such ``mongo:
socorro.external.mongodb`` and now you can add classes that get found
in ``socorro/external/mongodb/``.
