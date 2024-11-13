.. _socorro-test-checklist-chapter:

======================
Socorro Test Checklist
======================

Last updated: February 16th, 2023

This is a high-level system-wide checklist for making sure Socorro is working
correctly in a specific environment. It's a helpful template for figuring out
what you need to check if you're pushing out a significant change.

.. Note::

   This is used infrequently! If you're about to make a significant change, you
   should go through the checklist to make sure the checklist is correct and
   that everything is working as expected and fix anything that's wrong, THEN
   make your change and go through the checklist again.

Lonnen the bear says, "Only you can prevent production fires!"


How to use
==========

"Significant change" can mean any number of things, so this is just a template.
You should do the following:

1. Copy and paste the contents of this into a Google Doc or whatever system you
   plan to use to keep track of status and outstanding issues.

2. Go through what you copy-and-pasted, remove things that don't make sense,
   and add additional things that are important.

   Please uplift any changes via PR to this document that are interesting.


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

    * Run Django migrations

      Local dev environment:

      1. "just shell"
      2. "cd webapp/"
      3. "./manage.py showmigrations"

      -stage/-prod:

      1. See Confluence


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

    * Process some crash reports.
    * Check logs.

      * local dev environment: run the processor and look at stdout
      * stage/prod: check Google Cloud Console logging and filter for "error"

    * Check Grafana "processor.save_processed_crash" metric for appropriate
      environment.

      * localdev: Check METRICS logging in the console
      * stage: check Grafana stage dashboard
      * prod: check Grafana prod dashboard

    Is the processor saving crash data to Elasticsearch? To S3?

    * Check Grafana "processor.es.save_processed_crash"

    * Check Grafana "processor.s3.save_processed_crash"

    * Check Grafana "processor.telemetry.save_processed_crash"

    Submit a crash or reprocess a crash. Wait a few minutes. Use the
    CrashVerify API to verify the crash was processed and saved in all crash
    storage destinations.


    Webapp
    ======

    Is the webapp up?

    * Use a browser and check the healthcheck.

      * local dev: http://localhost:8000/__heartbeat__
      * stage: https://crash-stats.allizom.org/__heartbeat__
      * prod: https://crash-stats.mozilla.org/__heartbeat__

      It should say "ok: true".

    Is the webapp throwing errors?

    * Check Sentry for errors
    * Check logs for errors

    Do webapp errors make it to Sentry?

    * local dev: http://localhost:8000/__broken__ with username/password
    * stage: https://crash-stats.allizom.org/__broken__ with username/password
    * prod: https://crash-stats.mozilla.org/__broken__ with username/password

    Are there JavaScript errors in the webapp?

    * While checking individual pages below, open the DevTools console and
      watch for JavaScript errors.

    Can we log into the webapp?

    * Log in and check the profile page.

    Is the home page working?

    * Check /.
    * Make sure products are listed.
    * Make sure product links go to product home pages.
    * Make sure featured versions are listed in top nav bar.

    Is quick search from the navbar working?

    * Enter in a signature. Do you get search results?
    * Enter in a crash report id. Do you get a report view for that crash report?
    * Enter in "bp-" and the crash report id. Do you get a report view for that
      crash report?

    Go to Super Search. Is it working?

    * Click "Super Search" and make a search.
    * Facet on something like "products".
    * Add a column like "dom fission enabled".
    * Filter on a new field like "crash report keys" "contains" "Accessibility"

    Go to Top Crashers report.

    * Click on selection buttons. Do they filter the top crashers report?
    * Click on a signature. Does it go to the signature report page?

    Go to Signature Report.

    * Click through the tabs.
    * Add an additional aggregation. Try "dom fission enabled".

    Pick a crash report and go to report view.

    * Click through tabs.
    * Log out. Is it showing protected data?
    * Log in with account that has protected data access. Is it showing
      protected data?

    Test APIs.

    * RawCrash API
    * ProcessedCrash API
    * SuperSearch API
    * VersionString API


    Crontabber
    ==========

    Is the crontabber node working?

    * Check the Job and Log Django admin pages.

    Is cronrun throwing errors?

    * Check Sentry for errors
    * Check logs for errors


    Stage submitter
    ===============

    Is the stage submitter AWS Lambda job passing along crashes?

    * Check Datadog dashboard for stage collector to see if it's
      receiving crashes
