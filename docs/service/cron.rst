.. _cron-chapter:

===================
Service: Crontabber
===================

Socorro requires that certain upkeep jobs run periodically. For this, we have
a ``cronrun`` Django command that runs Django commands at scheduled times.

Job configuration is in ``webapp-django/crashstats/cron/__init__.py``.


What runs cronrun?
==================

There's a crontabber node that runs the Django ``cronrun`` command every
5 minutes.


How does it work?
=================

``cronrun`` can run any Django command at scheduled times. It supports several
features:

1. Arguments: Any arguments can be passed to the command.

2. Backfill: If a command hasn't run on schedule for some time, it will be
   run with all the time slots that it missed.

3. Last success: ``cronrun`` knows when the command last succeeded and
   can pass this in as an argument allowing the command to look at "all the
   things that happened since last I ran".

4. Error reporting: Errors are sent to Sentry.

5. Logging: All stdout is send to the logger.


Helper commands
===============

All commands are accessed in a shell in the app container. For example::

    $ make shell
    app@socorro:/app$ webapp-django/manage.py cronrun --help


**cronrun**
    Runs any scheduled jobs that need to be run.

**cronlist**
    Lists scheduled jobs and bookkeeping information.

**cronreset**
    Resets the state of specified jobs.

**cronmarksuccess**
    Marks specified jobs as successful.
