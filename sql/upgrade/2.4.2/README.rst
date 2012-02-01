2.4.2 Database Updates
======================

This batch makes the following database changes:

bug 722935
	Adds rows to the cronjobs table for all existing daily cronjobs
	
bug 722934
	adds architecture, and number of cores to reports clean
	in order to backfill several weeks, it may take hours to run
	
bug 722936
	adds tables for correlation reports

The above changes may take up to 4 hours to deploy.
This does not require a downtime, although it may cause the reports_clean hourly cronjob to fail and require backfill.