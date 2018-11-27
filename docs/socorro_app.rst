.. _socorro-app-chapter:

============================================
How app and an example works using configman
============================================

**July 18th, 2018:** This file is outdated.

The minimum app
===============

To illustrate the example, let's look at an example of an app that uses
``socorro_app`` to leverage ``configman`` to run. Let's look at
`weeklyReportsPartitions.py
<https://github.com/mozilla-services/socorro/blob/master/socorro/cron/weeklyReportsPartitions.py>`_

As you can see, it's a subclass of the `socorro.app.socorro_app.App
<https://github.com/mozilla-services/socorro/blob/master/socorro/app/socorro_app.py>`_
class which is a the-least-you-need wrapper for a minimal app. As you can see,
it takes care of logging and executing your ``main`` function.


Connecting and handling transactions
====================================

Connections are created and closed by the `ConnectionContext
<https://github.com/mozilla-services/socorro/blob/master/socorro/external/postgresql/connection_context.py#L11>`_
class.

The idea is that any external module (e.g. Boto, PostgreSQL, etc) can define a
``ConnectionContext`` class as per this model. What its job is is to create and
close connections and it has to do so in a contextmanager. What that means is
that you can do this::

  connector = ConnectionContext()
  with connector() as connection:  # opens a connection
      do_something(connection)
  # closes the connection

And if errors are raised within the ``do_something`` function it doesn't matter.
The connection will be closed.


What was the point of that?!
============================

For one thing, this app being a ``configman`` derived app means that all
configuration settings are as flexible as ``configman`` is. You can supply
different values for any of the options either by the command line (try running
``--help`` on the ``./weeklyReportsPartitions.py`` script) and you can control
them with various configuration files as per your liking.

The other thing to notice is that when writing another similar cron script, all
you need to do is to worry about exactly what to execute and let the framework
take care of transactions and opening and closing connections. Each class is
supposed to do one job and one job only.

``configman`` uses not only basic options such as ``database_password`` but also
more complex options such as aggregators. These are basically invariant options
that depend on each other and uses functions in there to get its stuff together.


How to override where config files are read
===========================================

``socorro_app`` supports multiple ways of picking up config files. The most
basic option is the `--admin.conf=` option. E.g.::

  python myapp.py --admin.conf=/path/to/my.ini

The default if you don't specify a ``--admin.conf`` is that it will look for a
``.ini`` file with the same name as the app. So if ``app_name='myapp'`` and you
start it like this::

  python myapp.py

it will automatically try to read ``config/myapp.ini`` and if you want to
override the directory it searches in you have to set an environment variable
called ``DEFAULT_SOCORRO_CONFIG_PATH`` like this::

  export DEFAULT_SOCORRO_CONFIG_PATH=/etc/socorro
  python myapp.py

Which means it will try to read ``/etc/socorro/myapp.ini``.

**NOTE:** If you specify a ``DEFAULT_SOCORRO_CONFIG_PATH`` that directory must
exist and be readable or else you will get an ``IOError`` when you try to start
your app.
