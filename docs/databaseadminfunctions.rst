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
in Socorro.

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
	

