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


week_begins_partition
---------------------

::

	week_begins_partition (
		partname TEXT
		)
	RETURNS timestamptz
	
	SELECT week_begins_partition ( 'reports_20111219' );
	
Given a partition table name, returns a timestamptz of the date and time that weekly partition starts.


week_ends_partition
-------------------

::

	week_ends_partition (
		partname TEXT
		)
	RETURNS timestamptz
	
	SELECT week_ends_partition ( 'reports_20111219' );
	
Given a partition table name, returns a timestamptz of the date and time that weekly partition ends.
	
	
week_begins_partition_string
----------------------------

::

	week_begins_partition_string (
		partname TEXT
		)
	RETURNS text
	
	SELECT week_begins_partition_string ( 'reports_20111219' );
	
Given a partition table name, returns a string of the date and time that weekly partition starts in the format 'YYYY-MM-DD HR:MI:SS UTC'.


week_ends_partition_string
--------------------------

::

	week_ends_partition_string (
		partname TEXT
		)
	RETURNS text
	
	SELECT week_ends_partition_string ( 'reports_20111219' );
	
Given a partition table name, returns a string of the date and time that weekly partition ends in the format 'YYYY-MM-DD HR:MI:SS UTC'.
	
	