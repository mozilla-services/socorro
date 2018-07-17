.. _socorro-test-checklist-chapter:

======================
Socorro Test Checklist
======================

This is a high-level system-wide checklist for making sure Socorro is working
correctly in a specific environment. It's a helpful template for figuring out
what you need to check if you're pushing out a significant change.

**Note:** This is used infrequently, so if you're about to make a significant change,
you should go through the checklist to make sure the checklist is correct and
that everything is working as expected and fix anything that's wrong, THEN
make your change, then go through the checklist again.

Lonnen the bear says, "Only you can prevent production fires!"

Last updated: February 6th, 2018


How to use
==========

"Significant change" can mean any number of things, so this is just a template.
You should do the following:

1. Copy and paste the contents of this into a Google Doc, Etherpad, or
   whatever system you plan to use to keep track of status and outstanding
   issues.

2. Go through what you copy-and-pasted, remove things that don't make sense,
   and add additional things that are important. (Please uplift any changes
   via PR to this document that are interesting.)


Checklist
=========

::

    Verify version
    ==============

    Before doing anything, verify the environment(s) that you're testing
    are running the version you expect.

    * local dev: http://localhost:8000/api/Status
    * -stage: https://crash-stats.allizom.org/api/Status
    * -prod: https://crash-stats.mozilla.com/api/Status


    Migrations
    ==========

    Make sure we can run migrations

    * Django migrations

      Local dev environment:

      1. "docker-compose run webapp bash"
      2. "cd webapp-django/"
      3. "./manage.py showmigrations"

      -stage/-prod:

      1. See Mana

    * Alembic migrations

      Local dev environment:

      1. "docker-compose run processor bash"
      2. "alembic -c docker/config/alembic.ini current"

      -stage/-prod:

      1. See Mana


    Collector (Antenna)
    ===================

    Is the collector handling incoming crashes?

    * Check datadog Antenna dashboard for the appropriate environment.

      localdev: Check the logging in the console
      stage: https://app.datadoghq.com/dash/272676/antenna--stage
      prod: https://app.datadoghq.com/dash/274773/antenna--prod

    * Log into Sentry and check for errors.

    * Submit a crash to the collector. Verify raw crash made it to S3.


    Processor
    =========

    Is the processor process running?

    * Log into a processor node and watch the processor logs for errors.

      Do: "journalctl -u socorro-processor -f"

      To check for errors grep for "ERRORS".

    * Check Datadog "processor.save_raw_and_processed" for appropriate
      environment.

      localdev: Check the logging in the console
      stage: https://app.datadoghq.com/dash/187676/socorro-stage-perf
      prod: https://app.datadoghq.com/dash/65215/socorro-prod

    Is the processor saving to ES? S3?

    * Check Datadog
      "processor.es.ESCrashStorageRedactedJsonDump.save_raw_and_processed.avg"

      stage: https://app.datadoghq.com/dash/187676/socorro-stage-perf
      prod: https://app.datadoghq.com/dash/65215/socorro-prod

    * Check Datadog
      "processor.s3.BotoS3CrashStorage.save_raw_and_processed" for
      appropriate environment.

      stage: https://app.datadoghq.com/dash/187676/socorro-stage-perf
      prod: https://app.datadoghq.com/dash/65215/socorro-prod


    Submit a crash or reprocess a crash. Wait a few minutes. Verify the crash was
    processed and made it to S3 and Elasticsearch.

    **FIXME:** We should write a script that uses envconsul to provide vars and takes
    a uuid via the command line and then checks all the things to make sure it's
    there. This assumes we don't already have one--we might!


    Webapp
    ======

    Is the webapp up?

    * Use a browser and check the healthcheck (/monitoring/healthcheck)

      It should say "ok: true".

    Is the webapp throwing errors?

    * Check Sentry for errors
    * Log into webapp node and check logs for errors.

      Do: "journalctl -u socorro-webapp -f"

      To check for errors, grep that for "ERROR".

    Do webapp errors make it to Sentry?

    * Log into the webapp, go to the Admin, and use the Crash Me Now tool

    Are there JavaScript errors in the webapp?

    * While checking individual pages below, open the DevTools console and watch
      for JavaScript errors.

    Can we log into the webapp?

    * Log in and check the profile page.

    Is the product home page working?

    * Check the Firefox product home page (/ redirects to /home/product/Firefox)

    Is super search working?

    * Click "Super Search" and make a search that is not likely to be cached.
      For example, filter on a specific date.

    Top Crashers Signature report and Report index

    1. Browse to Top Crashers
    2. Click on a crash signature to browse to Signature report
    3. Click on a crash ID to browse to report index


    Crontabber
    ==========

    Is crontabber working?

    * Check healthcheck endpoint (/monitoring/crontabber/)

      It should say ALLGOOD.

    * Check the webapp crontabber-state page (/crontabber-state/)

    Is crontabber throwing errors?

    * Check Sentry for errors
    * Log into admin node and check logs for errors

      Do: "tail -f /var/log/socorro/crontabber"

      To check for errors, grep for "ERROR".


    Stage submitter
    ===============

    Is the stage submitter AWS Lambda job passing along crashes?

    * Check Datadog dashboard for stage collector to see if it's
      receiving crashes
