.. index:: database

.. _databasemiscfunctions-chapter:

Database Misc Function Reference
================================

What follows is a listing of custom functions written for Socorro in the
PostgreSQL database which are useful for application development, but
do not fit in the "Admin" or "Datetime" categories.

Formatting Functions
====================

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
=============

These functions support the middleware, making it easier to look up
certain things in the database.

get_product_version_ids
------------------------

::

	get_product_version_ids (
		product CITEXT,
		versions VARIADIC CITEXT
	)
	
	
	
	
		
		





