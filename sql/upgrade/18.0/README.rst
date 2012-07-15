18.0 Database Updates
=====================

This batch makes the following database changes:

bug 755297
	Database changes to support Rapid Betas.

bug 737267
	Make reports_clean_done and dependant cron jobs take a "check_period"
	parameter.

...

The above changes will take 15 minutes or so for the initial changes,
and several hours for backfill.

This upgrade requires a processor and UI downtime during the initial
deployment, and output will tell you when it is safe to restart.
QA automation should not be run until backfill is complete.

This database deployment needs to be closely synchronized with the
application deployment.