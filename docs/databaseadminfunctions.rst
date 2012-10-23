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
-----------------

These functions manage the population of the many Materialized Views
in Socorro.  In general, for each matview there are two functions
which maintain it.  In the cases where these functions are not listed
below, assume that they fit this pattern.

::

	update_{matview_name} (
		updateday DATE optional default yesterday,
		checkdata BOOLEAN optional default true,
		check_period INTERVAL optional default '1 hour'
		)

	fills in one day of the matview for the first time
	will error if data is already present, or source data
	is missing

	backfill_{matview_name} (
		updateday DATE optional default yesterday,
		checkdata BOOLEAN optional default true,
		check_period INTERVAL optional default '1 hour'
		)

	deletes one day of data for the matview and recreates
	it.  will warn, but not error, if source data is missing
	safe for use without downtime

More detail on the parameters:

updateday
	UTC day to run the update/backfill for.  Also the UTC day
	to check for conflicting or missing dependant data.

checkdata
	Whether or not to check for conflicting data (i.e. has this
	already been run?), and for missing upstream data needed to
	run the fill.  If checkdata=false, function will just emit
	NOTICEs and return FALSE if upstream data is not present.

check_period
	For functions which depend on reports_clean, the window of
	reports_clean to check for data being present.  This is because
	at Mozilla we check to see that the last hour of reports_clean
	is filled in, but open source users need a larger window.

Matview functions return a BOOLEAN which will have one of three
results: TRUE, FALSE, or ERROR.  What these mean generally depend
on whether or not checkdata=on.  It also returns an error string
which gives more information about what it did.

If checkdata=TRUE (default):

TRUE
	matview function ran and filled in data.

FALSE
	matview update has already been run for the relevant period.
	no changes to data made, and warning returned.

ERROR
	underlying data is missing (i.e. no crashes, no raw_adu, etc.)
	or some unexpected error condition

IF checkdata=FALSE:

TRUE
	matview function ran and filled in data.

FALSE
	matview update has already been run for the relevant period,
	or source data (crashes, adu, etc.) is missing.
	no changes to data made, and no warning made.

ERROR
	some unexpected error condition.

Or, as a grid of results (where * indicates that a warning message is returned as well):

==============  =======  =======
Matview Proc        CheckData
--------------  ----------------
Condition        TRUE     FALSE
==============  =======  =======
Success          TRUE	  TRUE
Already Run      FALSE*   FALSE
No Source Data   ERROR*   FALSE*
Other Issue      ERROR*   ERROR*
==============  =======  =======

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

Hourly Matview Update Functions
-------------------------------

These need to be run every hour, for each hour.  None of them take the standard parameters.

.. csv-table::
	:header: "Matview","Update Function","Backfill Function","Depends On","Notes"
	:widths: 20,30,30,30,20

	"reports_duplicates","update_reports_duplicates","backfill_reports_duplicates",,
	"reports_clean","update_reports_clean","backfill_reports_clean","reports_duplicates, product_version",
	"product_version","update_product_versions","update_product_versions","ftpscraper","Cumulative"

Since update_product_versions is cumulative, it needs to only be run once.

Daily Matview Update Functions
------------------------------

These daily functions generally accept the parameters given above.  Unless otherwise noted,
all of them depend on all of the hourly functions having completed for the day.

.. csv-table::
	:header: "Matview","Update Function","Backfill Function","Depends On","Notes"
	:widths: 20,30,30,30,20

	"build_adu","update_build_adu","backfill_build_adu","raw_adu fill",
	"product_adu","update_adu","backfill_adu","raw_adu fill",
	"crashes_by_user","update_crashes_by_user","backfill_crashes_by_user","update_adu",
	"crashes_by_user_build","update_crashes_by_user_build","backfill_crashes_by_user_build","update_build_adu",
	"correlations","update_correlations","backfill_correlations","NA","Last Day Only"
	"correlations_addons","update_correlations","backfill_correlations","NA","Last Day Only"
	"correlations_cores","update_correlations","backfill_correlations","NA","Last Day Only"
	"correlations_modules",,,,"Not working at present."
	"daily_hangs","update_hang_report","backfill_hang_report",,
	"home_page_graph","update_home_page_graph","backfill_home_page_graph","product_adu",
	"home_page_graph_build","update_home_page_graph_build","backfill_home_page_graph_build","build_adu",
	"nightly_builds","update_nightly_builds","backfill_nightly_builds",,
	"signature_products","update_signatures","backfill_signature_counts",,
	"signature_products_rollup","update_signatures","backfill_signature_counts",,
	"tcbs","update_tcbs","backfill_tcbs",,
	"tcbs_build","update_tcbs_build","backfill_tcbs_build",,
	"explosiveness","update_explosiveness","backfill_explosiveness","tcbs","Last Day Only"

Functions marked "last day only" do not accumulate data, but display it only for the last
day they were run.  As such, there is no need to fill them in for each day.

Other Matview Functions
-----------------------

Matview functions which don't fit the parameters above include:

backfill_matviews
-----------------

Purpose: backfills data for all matviews for a specific range of dates.
For use when data is either missing or needs to be retroactively
corrected.

Called By: manually by admin as needed

::

  backfill_matviews (
    startdate DATE,
    optional enddate DATE default current_date,
    optional reportsclean BOOLEAN default true
  )

  SELECT backfill_matviews( '2011-11-01', '2011-11-27', false );
  SELECT backfill_matviews( '2011-11-01' );

startdate
  the first date to backfill

enddate
  the last date to backfill.  defaults to the current UTC date.

reportsclean
  whether or not to backfill reports_clean as well.
  defaults to true
  supplied because the backfill of reports_clean takes
  a lot of time.


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


update_product_versions
-----------------------

Purpose: updates the list of product_versions and product_version_builds
based on the contents of releases_raw.

Called By: daily cron job

::

	update_product_versions (
		)

	SELECT update_product_versions ( );

Notes: takes no parameters as the product update is always cumulative.  As of 2.3.5, only looks at product_versions with build dates in the last 30 days.  There is no backfill function because it is always a cumulative update.


update_rank_compare, backfill_rank_compare
------------------------------------------

Purpose: updates "rank_compare" based on the contents of the reports_clean table

Called By: daily cron job

Note: this matview is not historical, but contains only one day of data.  As
such, running either the update or backfill function replaces all existing data.
Since it needs an exclusive lock on the matview, it is possible (though
unlikely) for it to fail to obtain the lock and error out.


reports_clean_done
------------------

Purpose: supports other admin functions by checking if reports_clean is complete
	to the end of the day.

Called By: other udpate functions

::

	reports_clean_done (
		updateday DATE,
		check_period INTERVAL optional default '1 hour'
		)

	SELECT reports_clean_done('2012-06-12');
	SELECT reports_clean_done('2012-06-12','12 hours');


Schema Management Functions
----------------------------

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


try_lock_table
--------------

Purpose: attempt to get a lock on a table, looping with sleeps until
the lock is obtained.

Called by: various functions internally

::

	try_lock_table (
		tabname TEXT,
		mode TEXT optional default 'EXCLUSIVE',
		attempts INT optional default 20
	) returns BOOLEAN

	IF NOT try_lock_table('rank_compare', 'ACCESS EXCLUSIVE') THEN
		RAISE EXCEPTION 'unable to lock the rank_compare table for update.';
	END IF;

tabname
	the table name to lock
mode
	the lock mode per PostgreSQL docs.  Defaults to 'EXCLUSIVE'.
attempts
	the number of attempts to make, with 3 second sleeps between each.
	optional, defaults to 20.

Returns TRUE for table locked, FALSE for unable to lock.


create_table_if_not_exists
--------------------------

Purpose: creates a new table, skipping if the table is found to already
exist.

Called By: upgrade scripts

::

	create_table_if_not_exists (
		tablename TEXT,
		declaration TEXT,
		tableowner TEXT optional default 'breakpad_rw',
		indexes TEXT ARRAY default empty list
	)

	SELECT create_table_if_not_exists ( 'rank_compare', $q$
		create table rank_compare (
			product_version_id int not null,
			signature_id int not null,
			rank_days int not null,
			report_count int,
			total_reports bigint,
			rank_report_count int,
			percent_of_total numeric,
			constraint rank_compare_key primary key ( product_version_id, signature_id, rank_days )
		);$q$, 'breakpad_rw',
		ARRAY [ 'product_version_id,rank_report_count', 'signature_id' ]);

tablename
	name of the new table to create
declaration
	full CREATE TABLE sql statement, plus whatever other SQL statements you
	only want to run on table creation such as priming it with a few
	records and creating the primary key.  If running more than one
	SQL statement, separate them with semicolons.
tableowner
	the ROLE which owns the table.  usually 'breakpad_rw'.  optional.
indexes
	an array of sets of columns to create regular btree indexes on.
	use the array declaration as demonstrated above.  default is
	to create no indexes.

Note: this is the best way to create new tables in migration scripts, since
it allows you to rerun the script multiple times without erroring out.
However, be aware that it only checks for the existance of the table, not
its definition, so if you modify the table definition you'll need to
manually drop and recreate it.

add_column_if_not_exists
------------------------

Purpose: allow idempotent addition of new columns to existing tables.

Called by: upgrade scripts

::

	add_column_if_not_exists (
		tablename text,
		columnname text,
		datatype text,
		nonnull boolean default false,
		defaultval text default '',
		constrainttext text default ''
	) returns boolean

	SELECT add_column_if_not_exists (
		'product_version_builds','repository','citext' );

tablename
	name of the existing table to which to add the column
columname
	name of the new column to add
datatype
	data type of the new column to add
nonnull
	is the column NOT NULL?  defaults to false.  must have a default
	parameter if notnull.
defaultval
	default value for the column.  this will cause the table to
	be rewritten if set; beware of using on large tables.
constrainttext
	any constraint, including foreign keys, to be added to the
	column, written as a table constraint.  will cause the whole
	table to be checked; beware of adding to large tables.

Note: just checks if the table & column exist, and does nothing if they do.
does not check if data type, constraints and defaults match.

drop_old_partitions
-------------------

Purpose: to purge old raw data quarterly per data expiration policy.

Called By: manually by DBA.

::

	drop_old_partitions (
		mastername text,
		cutoffdate date
	) retruns BOOLEAN

	SELECT drop_old_partitions ( 'reports', '2011-11-01' );

mastername
	name of the partition master, e.g. 'reports', 'extensions', etc.
cutoffdate
	earliest date of data to retain.

Notes: drop_old_partitions assumes a table_YYYYMMDD naming format.
	It requires a lock on the partitioned tables, which generally
	means shutting down the processors.


Other Administrative Functions
------------------------------

add_old_release
---------------

Obsolete; Removed.

add_new_release
---------------

Purpose: allows admin users to manually add a release to the
releases_raw table.

Called By: admin interface

::

	add_new_release (
		product citext,
		version citext,
		release_channel citext,
		build_id numeric,
		platform citext,
		beta_number integer default NULL,
		repository text default 'release',
		update_products boolean default false,
		ignore_duplicates boolean default false
	) returns BOOLEAN

	SELECT add_new_release('Camino','5.0','release',201206271111,'osx');
	SELECT add_new_release('Camino','6.0','beta',201206271198,'osx',2,
		'camino-beta',true);

Notes: validates the contents of the required fields. If update_products=true, will run the update_products hourly job to process the new release into product_versions etc. If ignore_duplicates = true, will simply ignore duplicates instead of erroring on them.

edit_featured_versions
----------------------

Purpose: let admin users change the featured versions for a specific product.

Called By: admin interface

::

	edit_featured_versions (
		product citext,
		featured_versions LIST of text
	) returns BOOLEAN

	SELECT edit_featured_versions ( 'Firefox', '15.0a1','14.0a2','13.0b2','12.0' );
	SELECT edit_featured_versions ( 'SeaMonkey', '2.9.' );

Notes: completely replaces the list of currently featured versions.  Will check that versions featured have not expired.  Does not validate product names or version numbers, though.

add_new_product
---------------

Purpose: allows adding new products to the database.

Called By: DBA on new product request.

::

	add_new_product (
		prodname text,
		initversion major_version,
		prodid text default null,
		ftpname text default null,
		release_throttle numeric default 1.0
	) returns BOOLEAN

prodname
	product name, properly cased for display
initversion
	first major version number of the product which should appear
prodid
	"Product ID" for the product, if available
ftpname
	Product name in the FTP release repo, if different from display name
release_throttle
	If throttling back the number of release crashes processed, set here

Notes: add_new_product will return FALSE rather than erroring if the product already exists.
