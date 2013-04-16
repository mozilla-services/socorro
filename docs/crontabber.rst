.. index:: crontabber

.. _crontabber-chapter:

crontabber
==========

``crontabber`` is a script that handles all cron job scripting. Unlike
traditional UNIX ``crontab`` all execution is done via the
`./crontabber.py` script and the configuration about frequency and
exact time to run is part of the configuration files. The
configuration is done using ``configman`` and it looks something like
this::

    # name: jobs
    # doc: List of jobs and their frequency separated by `|`
    # converter: configman.converters.class_list_converter
    jobs=socorro.cron.jobs.foo.FooCronApp|12h
         socorro.cron.jobs.bar.BarCronApp|1d
         socorro.cron.jobs.pgjob.PGCronApp|1d|03:00

crontab runs crontabber
-----------------------

``crontabber`` can be run at any time. Because the exact execution
time is in configuration you can't accidentally execute jobs that
aren't supposed to execute simply by running ``crontabber``.

However, it can't be run as daemon. It actually needs to be run by
UNIX ``crontab`` every, say, 5 minutes. So instead of your ``crontab``
being a huge list of jobs at different times, all you need is this::

    */5 * * * * PYTHONPATH="..." socorro/cron/crontabber.py

That's all you need! Obviously the granularity of ``crontabber`` is
limited by the granularity you execute it.

By moving away from UNIX ``crontab`` we have better control of the
cron apps and their inter-relationship. We can also remove unnecessary
boilerplate cruft.

Dependencies
------------

In ``crontabber`` the state of previous runs of cron apps within are
remembered (stored internally in a JSON file) which makes it possible
to assign dependencies between the cron apps.

This is used to **potentially prevent running jobs**. Not to
automatically run those that depend. For example, if ``FooCronApp``
*depends* on ``BarCronApp`` it just won't run if ``BarCronApp`` last
resulted in an error or simply hasn't been run the last time it should.

Overriding dependencies is possible with the ``--force`` parameter.
For example, suppose you know ``BarCronApp`` can now be run you do
that like this::

    ./crontabber.py --job=BarCronApp --force

Dependencies inside the cron apps are defined by settings a class
attribute on the cron app. The attribute is called ``depends_on`` and
its value can be a string, a tuple or a list.
In this example, since ``BarCronApp``
depends on ``FooCronApp`` it's class would look something like this::

    from socorro.cron.crontabber import BaseCronApp

    class BarCronApp(BaseCronApp):
        app_name = 'BarCronApp'
        app_description = 'Does some bar things'
	depends_on = ('FooCronApp',)

        def run(self):
            ...

Own configurations
------------------

Each cron app can have its own configuration(s). Obviously they must
always have a good default that is good enough otherwise you can't run
``crontabber`` to run all jobs that are due. To make overrideable
configuration options add the ``required_config`` class attribute.
Here's an example::

    from configman import Namespace
    from socorro.cron.crontabber import BaseCronApp

    class FooCronApp(BaseCronApp):
        app_name = 'foo'

        required_config = Namespace()
        required_config.add_option(
            'bugzilla_url',
            default='https://bugs.mozilla.org',
            doc='Base URL for bugzilla'
        )

        def run(self):
            ...
            print self.config.bugzilla_url
            ...

Note: Inside that `run()` method in that example, the `self.config`
object is a special one. It's basically a reference to the
configuration specifically for this class but it has access to all
configuration objects defined in the "root". I.e. you can access
things like ``self.config.logger`` here too but other cron app won't
have access to ``self.config.bugzilla_url`` since that's unique to
this app.

To override cron app specific options on the command line you need to
use a special syntax to associate it with this cron app class.
Usually, the best hint of how to do this is to use ``python
crontabber.py --help``. In this example it would be::

    python crontabber.py --job=foo --class-FooCronApp.bugzilla_url=...

App names versus/or class names
-------------------------------

Every cron app in ``crontabber`` must have a class attribute called
``app_name``. This value must be unique. If you like, it can be the
same as the class it's in. When you list jobs you **list the full path
to the class** but it's the ``app_name`` within the found class that
gets remembered.

If you change the ``app_name`` all previously know
information about it being run is lost. If you change the name and
path of the class, the only other thing you need to change is the
configuration that refers to it.

Best practice recommendation is this:

* Name the class like a typical python class, i.e. capitalize and
  optionally camel case the rest. For example: ``UpdateADUCronApp``

* Optional but good practice is to keep the suffix ``CronApp`` to the
  class name.

* Make the ``app_name`` value lower case and replace spaces with ``-``.


Automatic backfilling
---------------------

``crontabber`` supports automatic backfilling for cron apps that need
a date (it's a python ``datetime.datetime`` instance) parameter which,
if all is well, defaults to the date right now.

To use backfilling your cron app needs to subclass another class.
Basic example::

    from socorro.crontabber import BaseBackfillCronApp

    class ThumbnailMoverCronApp(BaseBackfillCronApp):
        app_name = 'thumbnail-mover'
        app_version = 1.0
        app_description = 'moves thumbnails into /dev/null'

        def run(self, date):
            dir_ = '/some/path/' + date.strftime('%Y%m%d-%H%M%S')
            shutil.rmtree(dir_)

There's also a specific subclass for use with Postgres that uses
backfill::

    from socorro.crontabber import PostgresBackfillCronApp

    class ThumbnailUpdaterCronApp(PostgresBackfillCronApp):
        app_name = 'thumbnail-updater'
        app_version = 1.0
        app_description = 'marks thumbnails as moved'

        def run(self, connection, date):
            sql = """UPDATE thumbnails
            SET removed=true
            WHERE upload_date=%s
            """
            cursor = connection.cursor()
            cursor.execute(sql, date)

These cron apps are automatically backfilled because whenever they
wake up to run, they compare when it was last run with when it was
last successful. By also knowing the frequency it's easy to work out
how many times it's "behind". So, for example, if a job has a
frequency of 1 day; today is Friday and the last successful run was
Monday four days ago. That means, it needs to re-run the
``run(connection, date)`` method four times. One for Tuesday, one for
Wednesday, one for Thursday and one for today Friday. If, it fails
still the same thing will be repeated and re-tried the next day but
with one more date to re-run.

When backfilling across, say, three failed attempts. If the first of
those three fail, the ``last_success`` date is moved forward
accordingly.


Manual intervention
-------------------

First of all, to add a new job all you need to do is add it to the
config file that ``crontabber`` is reading from. Thanks to being a
``configman`` application it automatically picks up configurations
from files called ``crontabber.ini``, ``crontabber.conf`` or
``crontabber.json``. To create a new config file, use
``admin.dump_config`` like this::

    python socorro/cron/crontabber.py --admin.dump_conf ini

All errors that happen are reported to the standard python ``logging``
module. Also, the latest error (type, value and traceback) is stored
in the JSON database too. If any of your cron apps have an error you
can see it with::

    python socorro/cron/crontabber.py --list-jobs

Here's a sample output::

    === JOB ========================================================================
    Class:       socorro.cron.jobs.foo.FooCronApp
    App name:    foo
    Frequency:   12h
    Last run:    2012-04-05 14:49:56  (1 minute ago)
    Next run:    2012-04-06 02:49:56  (in 11 hours, 58 minutes)

    === JOB ========================================================================
    Class:       socorro.cron.jobs.bar.BarCronApp
    App name:    bar
    Frequency:   1d
    Last run:    2012-04-05 14:49:56  (1 minute ago)
    Next run:    2012-04-06 14:49:56  (in 23 hours, 58 minutes)
    Error!!      (1 times)
      File "socorro/cron/crontabber.py", line 316, in run_one
        self._run_job(job_class)
      File "socorro/cron/crontabber.py", line 369, in _run_job
        instance.main()
      File "/Use[snip]orro/socorro/cron/crontabber.py", line 47, in main
        self.run()
      File "/Use[snip]orro/socorro/cron/jobs/bar.py", line 10, in run
        raise NameError('doesnotexist')

It will only keep the latest error but it will include an
error count that tells you how many times it has tried and failed. The
error count increments every time **any** error happens and is reset
once no error happens. So, only the latest error is kept and to find
out about past error you have to inspect the log files.

NOTE: If a cron app that is configured to run every 2 days runs into
an error; it will try to run again in 2 days.

So, suppose you inspect the error and write a fix. If you're impatient
and don't want to wait till it's time to run again, you can start it
again like this::

    python socorro/cron/crontabber.py --job=my-app-name
    # or if you prefer
    python socorro/cron/crontabber.py --job=path.to.MyCronAppClass

This will attempt it again and no matter if it works or errors it will
pick up the frequency from the configuration and update what time it
will run next.

Resetting a job
---------------

If you want to pretend that a job has never run before you can use the
``--reset`` switch. It expects the name of the app. Like this::

    python socorro/cron/crontabber.py --reset=my-app-name

That's going to wipe that job out of the state database rendering
basically as if it's never run before. That can make this tool useful
for bootstrapping new apps that don't work on the first run or you
know what you're doing and you just want it to start afresh.

Nagios monitoring
-----------------

To hook up crontabber to Nagios monitoring as an NRPE plugin you can
use the ``--nagios`` switch like this::

    python socorro/cron/crontabber.py --nagios

What this will do is the following:

1. If there are no recorded errors in any app, exit with code 0 and no
   message.

2. If an app has exactly 1 error count, then:

  1. If it's backfill based (meaning it should hopefully self-heal) it
     will exit with code 1 and a message to ``stdout`` that starts with
     the word ``WARNING`` and also prints the name of the app, the name
     of the class, the exception type and the exception value.

  2. If it's **not** a backfill based app, it will exit with code 3 and a
     message on ``stdout`` starting with the word ``CRITICAL`` followed
     by the name of the app, the name of the class, the exception type
     and the exception value.

Frequency and execution time
----------------------------

The format for configuring jobs looks like this::

         socorro.cron.jobs.bar.BarCronApp|30m

or like this::

         socorro.cron.jobs.pgjob.PGCronApp|2d|03:00

Hopefully the format is self-explanatory. The first number is required
and it must be a number followed by "y", "d", "h" or "m". (years,
days, hours, minutes).

For jobs that have a frequency longer than 24 hours you can specify
exactly when it should run. This format has to be in the 24-hour
format of ``HH:MM``.

If you're ever uncertain that your recent changes to the configuration
file is correct or not, instead of waiting around you can check it
with::

    python socorro/cron/crontabber.py --configtest

which will do nothing if all is OK.

Timezone and UTC
----------------

All dates and times are in UTC. All Python ``datetime.datetime``
instances as non-native meaning they have a ``tzinfo`` value which is
set to ``UTC``.

This means that if you're an IT or ops person configuring a job to run
at 01:00 it's actually at 7pm pacific time.

Writing cron apps (aka. jobs)
-----------------------------

Because of the configurable nature of the ``crontabber`` the actual
cron apps can be located anywhere. For example, if it's related to
``HBase`` it could for example be in
``socorro/external/hbase/mycronapp.py``. However, for the most part
it's probably a good idea to write them in ``socorro/cron/jobs/`` and
write one class per file to make it clear. There are already some
"sample apps" in there that does nothing except serving as good
examples. With time, we can hopefully delete these as other, real
apps, can work as examples and inspiration.

The most common apps will be execution of certain specific pieces of
SQL against the PostgreSQL database. For those, the
``socorro/cron/jobs/pgjob.py`` example is good to look at. At the time
of writing it looks like this::

    from socorro.cron.crontabber import PostgresCronApp

    class PGCronApp(PostgresCronApp):
        app_name = 'pg-job'
        app_description = 'Does some foo things'

        def run(self, connection):
            cursor = connection.cursor()
            cursor.execute('select relname from pg_class')

Let's pick that a part a bit...
The most important difference is the different base class. Unlike the
``BaseCronApp`` class, this one is executing the ``run()`` method with
a connection instance as the one and only parameter. That connection
will **NOT** automatically take care of transactions! That means that you
have to manually handle that if it's applicable. For example, you
might add the code with a ``connection.commit()`` in Python or if it's
a chunk of SQL you add ``COMMIT;`` at the end of it.

But suppose you want to let ``crontabber`` handle the transactions you
can do that by instead of using ``PostgresCronApp`` as your base
class for a cron app you instead use::

    from socorro.cron.crontabber import PostgresTransactionManagedCronApp

With that, you can allow ``crontabber`` take care of any potential
error handling for you. For example, this would work then as expected::

    from socorro.cron.crontabber import PostgresTransactionManagedCronApp

    class MyPostgresCronApp(PostgresTransactionManagedCronApp):
        ...

        def run(self, connection):
            cursor = connection.cursor()
            today = datetime.datetime.today()
            cursor.execute('INSERT INTO jobs (room) VALUES (bathroom)')
            if today.strftime('%A') in ('Saturday', 'Sunday'):
                raise ValueError("Today is not a good day!")
            else:
                cursor.execute('INSERT INTO jobs(tool) VALUES (brush)')

Silly example but hopefully it's clear enough.

Raising an error inside a cron app **will not stop the other jobs**
from running other than the those that depend on it.


Testing crontabber jobs manually
--------------------------------

We have unit tests for crontabber jobs (located in: socorro/cron/jobs), but sometimes it is helpful to test these jobs locally before deploying changes.

For "backfill-based" jobs, you will need to reset them to run them immediately -- rather than waiting for the next available time period for running them.

Example::

    PYTHONPATH=. socorro/cron/crontabber.py --admin.conf=config/crontabber.ini --reset-job=ftpscraper

Then you can run them::

    PYTHONPATH=. socorro/cron/crontabber.py --admin.conf=config/crontabber.ini --job=ftpscraper

To dump a configuration file initially::

    PYTHONPATH=. socorro/cron/crontabber.py --admin.dump=ftpscraper.ini --job=ftpscraper

Check that configuration over and then add it to your config. config/crontabber.ini-dist is our default config file from the distro.
