.. index:: generic_app

.. _generic_app-chapter:

How generic app and an example works using configman
====================================================

The minimum app
---------------

To illustrate the example, let's look at an example of an app that
uses ``generic_app`` to leverage ``configman`` to run. Let's look at `weeklyReportsPartitions.py
<https://github.com/mozilla/socorro/blob/master/socorro/cron/weeklyReportsPartitions.py>`_

As you can see, it's a subclass of the `socorro.app.generic_app.App
<https://github.com/mozilla/socorro/blob/master/socorro/app/generic_app.py>`_
class which is a the-least-you-need wrapper for a minimal app. As you
can see, it takes care of logging and executing your ``main`` function.


Connecting and handling transactions
------------------------------------

Let's go back to the ``weeklyReportsPartitions.py`` cron script and take
a look at what it does.

It only really has one ``configman`` option and that's the
``transaction_executor_class``. The default value is
`TransactionExecutorWithBackoff
<https://github.com/mozilla/socorro/blob/master/socorro/database/transaction_executor.py#L59>`_
which is the class that's going to take care of two things:

1. execute a callable that accepts an opened database connection as
   first and only parameter

2. committing the transaction if there are no errors and rolling back
   the transaction if an exception is raised

3. NB: if an ``OperationalError`` or ``InterfaceError`` exception is
   raised, ``TransactionExecutorWithBackoff`` will log that and retry
   after configurable delay

Note that ``TransactionExecutorWithBackoff`` is the default
``transaction_executor_class`` but if you override it,  for example by the command
line, with ``TransactionExecutor`` no exceptions are swallowed and it
doesn't retry.

Now, connections are created and closed by the `ConnectionContext
<https://github.com/mozilla/socorro/blob/master/socorro/external/postgresql/connection_context.py#L11>`_
class. As you might have noticed, the default ``database_class`` defined
in the ``TransactionExecutor`` is
``socorro.external.postgresql.connection_context.ConnectionContext`` as
you can see `here
<https://github.com/mozilla/socorro/blob/master/socorro/database/transaction_executor.py#L29>`_

The idea is that any external module (e.g. HBase, PostgreSQL, etc)
can define a ``ConnectionContext`` class as per this model. What its job
is is to create and close connections and it has to do so in a
contextmanager. What that means is that you can do this::

 connector = ConnectionContext()
 with connector() as connection:  # opens a connection
     do_something(connection)
 # closes the connection

And if errors are raised within the ``do_something`` function it
doesn't matter. The connection will be closed.


What was the point of that?!
----------------------------

For one thing, this app being a ``configman`` derived app means that all
configuration settings are as flexible as ``configman`` is. You can supply
different values for any of the options either by the command line
(try running ``--help`` on the ``./weeklyReportsPartitions.py`` script)
and you can control them with various configuration files as per your
liking.

The other thing to notice is that when writing another similar cron
script, all you need to do is to worry about exactly what to execute
and let the framework take care of transactions and opening and
closing connections. Each class is supposed to do one job and one job
only.

``configman`` uses not only basic options such as ``database_password``
but also more complex options such as aggregators. These are basically
invariant options that depend on each other and uses functions in
there to get its stuff together.


How to override where config files are read
-------------------------------------------

``generic_app`` supports multiple ways of picking up config files.
The most basic option is the `--admin.conf=` option. E.g.::

 python myapp.py --admin.conf=/path/to/my.ini

The default if you don't specify a ``--admin.conf`` is that it will
look for a ``.ini`` file with the same name as the app. So if
``app_name='myapp'`` and you start it like this::

 python myapp.py

it will automatically try to read ``config/myapp.ini`` and if you want
to override the directory it searches in you have to set an
environment variable called ``DEFAULT_SOCORRO_CONFIG_PATH`` like this::

 export DEFAULT_SOCORRO_CONFIG_PATH=/etc/socorro
 python myapp.py

Which means it will try to read ``/etc/socorro/myapp.ini``.

**NOTE:** If you specify a ``DEFAULT_SOCORRO_CONFIG_PATH`` that
directory must exist and be readable or else you will get an
``IOError`` when you try to start your app.
