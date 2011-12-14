.. index:: database

.. _databasedatetimefunctions-chapter:

Custom Time-Date Functions
==========================

The present Socorro database needs to do a lot of time, date and timezone manipulation.  This is partly a natural consequence of the application, and the need to use both DATE and TIMESTAMPTZ values.  The greater need is legacy timestamp, conversion, however; currently the processors save crash reporting timestamps as TIMESTAMP WITHOUT TIMEZONE in Pacific time, whereas the rest of the database is TIMESTAMP WITH TIME ZONE in UTC.  This necessitates a lot of tricky time zone conversions.

The functions below are meant to make it easier to write queries which return correct results based on dates and timestamps.

tstz_between
------------

::

	tstz_between (
		tstz TIMESTAMPTZ,
		bdate DATE,
		fdate DATE 
	)
	RETURNS BOOLEAN
		
	SELECT tstz_between ( '2011-11-25 15:23:11-08',
		'2011-11-25', '2011-11-26' );
	
Checks whether a timestamp with time zone is between two UTC dates, inclusive of the entire ending day.

utc_day_is
----------

::

	utc_day_is (
		TIMESTAMPTZ,
		TIMESTAMP or DATE
		)
	RETURNS BOOLEAN
	
	SELECT utc_day_is ( '2011-11-26 15:23:11-08', '2011-11-28' );
	
Checks whether the provided timestamp with time zone is within the provided UTC day, expressed as either a timestamp without time zone or a date.


utc_day_near
------------

::

	utc_day_near (
		TIMESTAMPTZ,
		TIMESTAMP or DATE
		)
	RETURNS BOOLEAN
	
	SELECT utc_day_near ( '2011-11-26 15:23:11-08', '2011-11-28' );
	
Checks whether the provided timestamp with time zone is within an hour of the provided UTC day, expressed as either a timestamp without time zone or a date.  Used for matching when related records may cross over midnight.


utc_day_begins_pacific
----------------------

::

	utc_day_begins_pacific (
		DATE
		)
	RETURNS TIMESTAMP WITHOUT TIME ZONE
	
	SELECT utc_day_begins_pacific ( '2011-11-28' );
	returns: '2011-11-27 16:00:00'
	
Given as specific date as a UTC day, returns as a timestamp without time zone the date and time in the Pacific time zone when that day begins.  Used primarily to compare UTC days against reports.date_processed.  DST-sensitive.


utc_day_ends_pacific
--------------------

::

	utc_day_ends_pacific (
		DATE
		)
	RETURNS TIMESTAMP WITHOUT TIME ZONE
	
	SELECT utc_day_begins_pacific ( '2011-11-28' );
	returns: '2011-11-28 16:00:00'
	
	reports.date_processed >= utc_day_begins_pacific('2011-11-27')
		AND reports.date_processed < utc_day_ends_pacific('2011-11-29')
	

Given as specific date as a UTC day, returns as a timestamp without time zone the date and time in the Pacific time zone when that day ends.  Used primarily to compare UTC days against reports.date_processed.  DST-sensitive.


ts2pacific
----------

::

	ts2pacific (
		TIMESTAMP
		)
	RETURNS TIMESTAMPTZ
	
	SELECT ts2pacific ( '2011-11-25 13:33:20' );
	
Given a timestamp without time zone, assumed to be in the Pacific time zone, converts it to a timestamp with time zone.


tz2pac_ts
---------

::

	tz2pac_ts (
		TIMESTAMPTZ
		)
	RETURNS TIMESTAMP
	
	SELECT tz2pac_ts ( '2011-11-25 21:33:20-00' );
	
Given a timestamp with time zone, converts it to a timestamp without time zone in Pacific time.


week_begins_utc
---------------

:: 

	week_begins_utc (
		TIMESTAMP or DATE
		)
	RETURNS timestamptz
	
	SELECT week_begins_utc ( '2011-11-25' );
	
Given a timestamp or date, returns the timestamp with time zone corresponding to the beginning of the week in UTC time.  Used for partitioning data by week.


week_ends_utc
-------------

:: 

	week_ends_utc (
		TIMESTAMP or DATE
		)
	RETURNS timestamptz
	
	SELECT week_ends_utc ( '2011-11-25' );
	
Given a timestamp or date, returns the timestamp with time zone corresponding to the end of the week in UTC time.  Used for partitioning data by week.


	
	
	
	