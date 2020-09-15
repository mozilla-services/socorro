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

    * local dev: http://localhost:8000/__version__
    * -stage: https://crash-stats.allizom.org/__version__
    * -prod: https://crash-stats.mozilla.org/__version__


    Migrations
    ==========

    Make sure we can run migrations

    * Django migrations

      Local dev environment:

      1. "make shell"
      2. "cd webapp-django/"
      3. "./manage.py showmigrations"

      -stage/-prod:

      1. See Mana


    Collector (Antenna)
    ===================

    Is the collector handling incoming crashes?

    * Check Grafana dashboard for the appropriate environment.

      * localdev: Check the logging in the console
      * stage: https://earthangel-b40313e5.influxcloud.net/d/mTjlP_8Zz/socorro-stage-megamaster-remix?orgId=1
      * prod: https://earthangel-b40313e5.influxcloud.net/d/LysVjx8Zk/socorro-prod-megamaster-remix?orgId=1

    * Log into Sentry and check for errors.

    * Submit a crash to the collector. Verify raw crash made it to S3.


    Processor
    =========

    Is the processor process running?

    * Log into a logging node and check logs for errors:

      Do: "tail -f /var/log/raw/socorro.processor.docker.processor.log"

      To check for errors grep for "ERRORS".

    * Check Grafana "processor.save_processed_crash" for appropriate
      environment.

      * localdev: Check the logging in the console
      * stage: https://earthangel-b40313e5.influxcloud.net/d/mTjlP_8Zz/socorro-stage-megamaster-remix?orgId=1
      * prod: https://earthangel-b40313e5.influxcloud.net/d/LysVjx8Zk/socorro-prod-megamaster-remix?orgId=1

    Is the processor saving to ES? S3?

    * Check Grafana
      "processor.es.ESCrashStorageRedactedJsonDump.save_processed_crash.avg"

    * Check Grafana
      "processor.s3.BotoS3CrashStorage.save_processed_crash" for
      appropriate environment.

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
    * Log into a logging node and check logs for errors:

      Do: "tail -f /var/log/raw/socorro.webapp.docker.webapp.log"

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

    Is the crontabber node working?

    * Check the Job and Log Django admin pages.

    Is cronrun throwing errors?

    * Check Sentry for errors
    * Log into a logging node and check logs for errors:

      Do: "tail -f /var/log/raw/socorro.crontabber.docker.crontabber.log"

      To check for errors, grep for "ERROR".


    Stage submitter
    ===============

    Is the stage submitter AWS Lambda job passing along crashes?

    * Check Datadog dashboard for stage collector to see if it's
      receiving crashes
