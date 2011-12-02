.. index:: database

.. _databaseadminfunctions-chapter:

Database Admin Function Reference
=================================

What follows is a listing of custom functions written for Socorro in the
PostgreSQL database which are intended for database administration,
particularly scheduled tasks.   Many of these functions depend on other,
internal functions which are not documented.

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
	

