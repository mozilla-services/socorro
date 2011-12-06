.. index:: database

.. _databaseadminfunctions-chapter:

Database Admin Function Reference
=================================

What follows is a listing of custom functions written for Socorro in the
PostgreSQL database which are intended for database administration,
particularly scheduled tasks.   Many of these functions depend on other,
internal functions which are not documented.

All functions below return BOOLEAN, with TRUE meaning completion, and 
throw an ERROR if they fail, unless otherwise noted.

MatView Functions
=================

These functions manage the population of the many Materialized Views
in Socorro.  In general, for each matview there are two functions
which maintain it:

::

	update_{matview_name} ( DATE )
	
	fills in one day of the matview for the first time
	will error if data is already present, or source data
	is missing
	
	backfill_{matview_name} ( DATE )
	
	deletes one day of data for the matview and recreates
	it.  will warn, but not error, if source data is missing
	safe for use without downtime
	
Exceptions to the above are generally for procedures which need to 
run hourly or more frequently (e.g. update_reports_clean,
reports_duplicates).  Also, some functions have shortcut names where
they don't use the full name of the matview (e.g. update_adu).

Note that the various matviews can take radically different amounts
of time to update or backfill ... from a couple of seconds to 10 
minutes for one day.

In addition, there are several procedures which are designed to
update or backfill multiple matviews for a range of days.  These
are designed for when there has been some kind of widespread issue
in crash processing and a bunch of crashes have been reprocessed
and need to be re-aggregated.  

These mass-backfill functions generally give a lot of command-line
feedback on their progress, and should be run in a screen session,
as they may take hours to complete.  These functions, as the most
generally used, are listed first. If you are doing a mass-backfill, 
you probably want to limit
the backfill to a week at a time in order to prevent it from running
too long before committing.


backfill_all_matviews
---------------------

Purpose: backfills data for all matviews for a specific range of dates.
For use when data is either missing or needs to be retroactively 
corrected.

Called By: manually by admin as needed

::

  backfill_all_matviews (
    startdate DATE,
    optional enddate DATE default current_date,
    optional reportsclean BOOLEAN default true 
  )

  SELECT backfill_all_matviews( '2011-11-01', '2011-11-27', false );
  SELECT backfill_all_matviews( '2011-11-01' );

startdate
  the first date to backfill
  
enddate
  the last date to backfill.  defaults to the current UTC date.
  
reportsclean
  whether or not to backfill reports_clean as well.  
  defaults to true
  supplied because the backfill of reports_clean takes
  a lot of time.
  
  
backfill_signature_counts
-------------------------
  
Purpose:  backfill all of the *_signature_counts tables.

Called By: admin as needed

::

	backfill_signature_counts (
		startdate DATE,
		enddate DATE
	)
	
	SELECT backfill_signature_counts ( '2011-11-01','2011-12-05' );
	
startdate, enddate
	starting and ending dates for the backfill.  dates are inclusive
	
  
backfill_reports_clean
----------------------

Purpose: backfill only the reports_clean normalized fact table. 

Called By: admin as needed

::

	backfill_reports_clean (
		starttime TIMESTAMPTZ,
		endtime TIMESTAMPTZ,
	)
	
	SELECT backfill_reports_clean ( '2011-11-17', '2011-11-29 14:00:00' );
	
starttime 
	timestamp to start backfill
	
endtime 
	timestamp to halt backfill at
	
Note: if backfilling less than 1 day, will backfill in 1-hour increments.  If backfilling more than one day, will backfill in 6-hour increments.  Can take a long time to backfill more than a couple of days.
   
  
update_adu, backfill_adu
------------------------

Purpose: updates or backfills one day of the product_adu table, which
is one of the two matviews powering the graphs in socorro.

Called By: update function called by the update_matviews cron job. 

::

	update_adu ( 
		updateday DATE 
		);
		
	backfill_adu (
		updateday DATE
		);
		
	SELECT update_adu('2011-11-26');

	SELECT backfill_adu('2011-11-26');
	
updateday
	DATE of the UTC crash report day to update or backfill
	
	
update_products
---------------

Purpose: updates the list of product_versions and product_version_builds 
based on the contents of releases_raw.

Called By: daily cron job

::

	update_products (
		)
		
	SELECT update_products ( '2011-12-04' );
	
Notes: takes no parameters as the product update is always cumulative.  As of 2.3.5, only looks at product_versions with build dates in the last 30 days.  There is no backfill function because it is always a cumulative update.


update_tcbs, backfill_tcbs
--------------------------

Purpose: updates "tcbs" based on the contents of the report_clean table

Called By: daily cron job

::

	update_tcbs (
		updateday DATE,
		checkdata BOOLEAN optional default true
		)
		
	SELECT update_tcbs ( '2011-11-26' );
	
	backfill_tcbs (
		updateday DATE
		)
		
	SELECT backfill_tcbs ( '2011-11-26' );
	
updateday
	UTC day to pull data for.
checkdata
	whether or not to check dependant data and throw an error if it's not found.
	
Notes: updates only "new"-style versions.  Until 2.4, update_tcbs pulled data directly from reports and not reports_clean.  


update_daily_crashes, backfill_daily_crashes
--------------------------------------------

Purpose: updates "daily_crashes" based on the contents of the report_clean table

Called By: daily cron job

::

	update_daily_crashes (
		updateday DATE,
		checkdata BOOLEAN optional default true
		)
		
	SELECT update_daily_crashes ( '2011-11-26' );
	
	backfill_daily_crashes (
		updateday DATE
		)
		
	SELECT backfill_daily_crashes ( '2011-11-26' );
	
updateday
	UTC day to pull data for.
checkdata
	whether or not to check dependant data and throw an error if it's not found.
	
Notes: updates only "new"-style versions.  Until 2.4, update_daily_crashes pulled data directly from reports and not reports_clean.  Probably the slowest of the regular update functions; can date up to 4 minutes to do one day.


Schema Management Functions
===========================

These functions support partitioning, upgrades, and other management
of tables and views.

weekly_report_partitions
------------------------

Purpose: to create new paritions for the reports table and its  child
tables every week.

Called By: weekly cron job

::

	weekly_report_partitions ( 
		optional numweeks integer default 2,
		optional targetdate date default current_date
	)
	
	SELECT weekly_report_partitions();
	SELECT weekly_report_partitions(3,'2011-11-09');

numweeks
	number of weeks ahead to create partitions
targetdate
	date for the starting week, if not today
	

