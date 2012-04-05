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
attribute on the cron app. In this example, since ``BarCronApp``
depends on ``FooCronApp`` it's class would look something like this::

    from socorro.cron.crontabber import BaseCronApp

    class BarCronApp(BaseCronApp):
        app_name = 'BarCronApp'
        app_description = 'Does some bar things'

        def run(self):
            ...

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


Manual intervention
-------------------

First of all, to add a new job all you need to do is add it to the
config file that ``crontabber`` is reading from. Thanks to being a
``crontabber`` application it automatically picks up configurations
from files called ``crontabber.ini``, ``crontabber.conf`` or
``crontabber.json``. To create a new config file, use
``admin.dump_config`` like this::

    python socorro/cron/crontabber.py --admin.dump_conf ini

All errors that happen are reported to the standard python ``logging``
module. Also, the latest error (type, value and traceback) is stored
in the JSON database too. If any of your cron apps have an error you
can see it with::

    python socorro/cron/crontabber.py --list-jobs

It will only keep the latest error but it will include an
error count that tells you how many times it has tried and failed.

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
