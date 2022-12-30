.. _cron-chapter:

==========
Crontabber
==========

Socorro requires that certain upkeep jobs run periodically. For this, we have
a ``cronrun`` Django command that runs Django commands at scheduled times.

Job configuration is in ``webapp-django/crashstats/cron/__init__.py``.

Code is in ``webapp-django/crashstats/cron/``.

Run script is ``/app/bin/run_crontabber.sh``. This is an infinite loop that
runs the ``manage.py cronrun`` command every 5 minutes.


manage.py cronrun
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


manage.py cronrun helper commands
=================================

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


Configuration
=============

``cronrun`` is a Django management command, so it's configured the same as
the webapp.


Running in a local dev environment
==================================

To run the processor in the local dev environment, do::

  $ docker compose up crontabber


Running in a server environment
===============================

Use the same configuration as the webapp with a ``webapp.env`` file.

Run the docker image using the ``crontabber`` command. Something like this::

    docker run \
        --env-file=webapp.env \
        mozilla/socorro_app crontabber
