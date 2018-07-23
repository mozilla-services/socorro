.. _crontabber-chapter:

===================
Service: Crontabber
===================

Crontabber is a project that manages scheduled tasks. Unlike traditional UNIX
crontab, all execution is done via the crontabber script and the configuration
about frequency and exact time to run is part of the configuration files.

The configuration is done using ``configman`` and can be specified in a ``.ini``
file or in the process environment. An example looks like this::

  # name: jobs
  # doc: List of jobs and their frequency separated by `|`
  # converter: configman.converters.class_list_converter
  jobs=socorro.cron.jobs.foo.FooCronApp|12h
       socorro.cron.jobs.bar.BarCronApp|1d
       socorro.cron.jobs.pgjob.PGCronApp|1d|03:00


The default jobs specification lives in ``socorro/cron/crontabber_app.py`` as
``DEFAULT_JOBS``.

Different server environments use different jobs specifications based on
``DEFAULT_JOBS``.


What runs crontabber?
=====================

Every 5 minutes, ``crontabber`` runs, updates crontabber jobs bookkeeping,
checks which jobs need to run, and runs those jobs.


Crontabber theory
=================

Crontabber runs a set of jobs.

A job specification includes the class to run, a frequency, and optionally a
specific time to run at. In this way, we can specify jobs to run weekly, daily,
hourly, daily at a specific time, and so on.

Crontabber maintains some bookkeeping for each job including when the job was
first run, most recently run, the time of the last success, the time of the last
failure, and the next run. If the job failed, it logs some error information.

Jobs can have zero or more dependencies on other jobs. Crontabber makes sure
that dependencies are filled before running a job. For example, if
``FooCronApp`` *depends* on ``BarCronApp`` it just won't run if ``BarCronApp``
last resulted in an error or simply hasn't been run the last time it should.

Crontabber has several command line arguments that let you override the job spec
to run things manually. For example, you can override dependencies for a job
with the ``--force`` parameter like this::

    socorro-cmd crontabber --job=BarCronApp --force

Dependencies inside the cron apps are defined by settings a class attribute on
the cron app. The attribute is called ``depends_on`` and its value can be a
string, a tuple or a list. In this example, since ``BarCronApp`` depends on
``FooCronApp`` it's class would look something like this::

    from crontabber.base import BaseCronApp

    class BarCronApp(BaseCronApp):
        app_name = 'BarCronApp'
        app_description = 'Does some bar things'
        depends_on = ('FooCronApp',)

        def run(self):
            ...

Raising an error inside a cron app **will not stop the other jobs** from running
other than the those that depend on it.


App names and class names
=========================

Every cron app in ``crontabber`` must have a class attribute called
``app_name``. This value must be unique. If you like, it can be the same as the
class it's in. When you list jobs you **list the full path to the class** but
it's the ``app_name`` within the found class that gets remembered.

If you change the ``app_name`` all previously know information about it being
run is lost. If you change the name and path of the class, the only other thing
you need to change is the configuration that refers to it.

Best practice recommendation is this:

* Name the class like a typical Python class, i.e. capitalize and optionally
  camel case the rest. For example: ``FooCronApp``

* Optional but good practice is to keep the suffix ``CronApp`` to the class
  name.

* Make the ``app_name`` value lower case and replace spaces with ``-``.


Automatic backfilling
=====================

``crontabber`` supports automatic backfilling for cron apps that need a date
(it's a python ``datetime.datetime`` instance) parameter which, if all is well,
defaults to the date right now.

To use backfilling your cron app needs to subclass another class. Basic
example::

    from socorro.cron.base import BaseBackfillCronApp

    class ThumbnailMoverCronApp(BaseBackfillCronApp):
        app_name = 'thumbnail-mover'
        app_version = 1.0
        app_description = 'moves thumbnails into /dev/null'

        def run(self, date):
            dir_ = '/some/path/' + date.strftime('%Y%m%d-%H%M%S')
            shutil.rmtree(dir_)


There's also a specific subclass for use with Postgres that uses backfill::

    from socorro.cron.base import PostgresBackfillCronApp

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


These cron apps are automatically backfilled because whenever they wake up to
run, they compare when it was last run with when it was last successful. By also
knowing the frequency it's easy to work out how many times it's "behind". So,
for example, if a job has a frequency of 1 day; today is Friday and the last
successful run was Monday four days ago. That means, it needs to re-run the
``run(connection, date)`` method four times. One for Tuesday, one for Wednesday,
one for Thursday and one for today Friday. If, it fails still the same thing
will be repeated and re-tried the next day but with one more date to re-run.

When backfilling across, say, three failed attempts. If the first of those three
fail, the ``last_success`` date is moved forward accordingly.


Troubleshooting
===============

Examining the last error
------------------------

All errors that happen are reported to the standard python ``logging`` module.
Also, the latest error (type, value and traceback) is stored in the JSON
database too. If any of your cron apps have an error you can see it with::

    socorro-cmd crontabber --list-jobs


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
      File "socorro/cron/crontabber_app.py", line 316, in run_one
        self._run_job(job_class)
      File "socorro/cron/crontabber_app.py", line 369, in _run_job
        instance.main()
      File "/Use[snip]orro/socorro/cron/crontabber_app.py", line 47, in main
        self.run()
      File "/Use[snip]orro/socorro/cron/jobs/bar.py", line 10, in run
        raise NameError('doesnotexist')


It will only keep the latest error but it will include an error count that tells
you how many times it has tried and failed. The error count increments every
time **any** error happens and is reset once no error happens. So, only the
latest error is kept and to find out about past error you have to inspect the
log files.

.. NOTE::

   If a cron app that is configured to run every 2 days runs into an error, it
   will try to run again in 2 days.


Running a job manually
----------------------

Suppose you inspect the error and write a fix. If you're impatient and don't
want to wait till it's time to run again, you can start it again like this::

    socorro-cmd crontabber --job=my-app-name


This will attempt it again and no matter if it works or errors it will pick up
the frequency from the configuration and update what time it will run next.


Resetting a job
---------------

If you want to pretend that a job has never run before you can use the
``--reset`` switch. It expects the name of the app. Like this::

    socorro-cmd crontabber --reset=my-app-name

That's going to wipe that job out of the state database rendering basically as
if it's never run before. That can make this tool useful for bootstrapping new
apps that don't work on the first run or you know what you're doing and you just
want it to start afresh.


Figuring out configuration parameters
-------------------------------------

Best way to figure out the keys for configuration parameters is by running
crontabber and telling it to list the jobs. It'll spit out all the configuration
keys at startup.


Scheduling jobs
===============

The format for configuring jobs looks like this::

  socorro.cron.jobs.bar.BarCronApp|30m

or like this::

  socorro.cron.jobs.pgjob.PGCronApp|2d|03:00

Hopefully the format is self-explanatory. The first number is required and it
must be a number followed by "y" (years), "d" (days), "h" (hours), or "m"
(minutes).

For jobs that have a frequency longer than 24 hours you can specify exactly when
it should run. This format has to be in the 24-hour format of ``HH:MM``.

If you're ever uncertain that your recent changes to the configuration file is
correct or not, instead of waiting around you can check it with::

  socorro-cmd crontabber --configtest


which will do nothing if all is OK.


Timezone and UTC
================

All dates and times are in UTC. All Python ``datetime.datetime`` instances as
non-native meaning they have a ``tzinfo`` value which is set to ``UTC``.

This means that if you're an IT or ops person configuring a job to run at 01:00
it's actually at 7pm pacific time.


Writing cron apps (aka. jobs)
=============================

First off, if you can implement whatever you're implementing as something other
than a crontabber job, do that. If not, proceed.

Code for crontabber jobs goes in ``socorro/cron/jobs/``.

Make sure to write tests for them if you can.


Testing crontabber jobs manually
================================

We have unit tests for crontabber jobs (located in: socorro/cron/jobs), but
sometimes it is helpful to test these jobs locally before deploying changes.

For "backfill-based" jobs, you will need to reset them to run them immediately
rather than waiting for the next available time period for running them.

Example::

    $ socorro-cmd crontabber --reset-job=ftpscraper

Then you can run them::

    $ socorro-cmd crontabber --job=ftpscraper
