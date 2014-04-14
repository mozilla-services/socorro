.. index:: database

.. _databasemiscfunctions-chapter:

Database Misc Function Reference
================================

What follows is a listing of custom functions written for Socorro in the
PostgreSQL database which are useful for application development, but
do not fit in the "Admin" or "Datetime" categories.

Formatting Functions
--------------------

build_numeric
-------------

::

	build_numeric (
		build TEXT
	)
	RETURNS NUMERIC

	SELECT build_numeric ( '20110811165603' );

Converts a build ID string, as supplied by the processors/breakpad, into
a numeric value on which we can do computations and derive a date.  Returns
NULL if the build string is a non-numeric value and thus corrupted.


build_date
----------

::

	build_date (
		buildid NUMERIC
	)
	RETURNS DATE

	SELECT build_date ( 20110811165603 );

Takes a numeric build_id and returns the date of the build.


API Functions
-------------

These functions support the middleware, making it easier to look up
certain things in the database.

get_product_version_ids
------------------------

::

	get_product_version_ids (
		product CITEXT,
		versions VARIADIC CITEXT
	)

	SELECT get_product_version_ids ( 'Firefox','11.0a1' );
	SELECT get_product_version_ids ( 'Firefox','11.0a1','11.0a2','11.0b1');

Takes a product name and a list of version_strings, and returns an array (list) of surrogate keys (product_version_ids) which can then be used in queries like:

::

	SELECT * FROM reports_clean WHERE date_processed BETWEEN '2012-03-21' AND '2012-03-38'
	WHERE product_version_id = ANY ( $list );

Mathematical Functions
----------------------

These functions do math operations which we need to do repeatedly, saving some typing.

crash_hadu
----------

::

	crash_hadu (
		crashes INT8,
		adu INT8,
		throttle NUMERIC default 1.0
	);
	returns NUMERIC (12,3)

Returns the "crashes per hundred ADU", by this formula:
( crashes / throttle ) * 100 / adu

Internal Functions
------------------

These functions are designed to be called by other functions, so are sparsely documented.

nonzero_string
--------------

::

	nonzero_string (
		TEXT or CITEXT
	) returns boolean

Returns FALSE if the string consists of '', only spaces, or NULL.  True otherwise.

validate_lookup
---------------

::

	validate_lookup (
		ltable TEXT,  -- lookup table name
		lcol TEXT, -- lookup column name
		lval TEXT, -- value to look up
		lmessage TEXT -- name of the entity in error messages
	) returns boolean

Returns TRUE if the value is present in the named lookup table.  Raises a custom ERROR if it's not present.










