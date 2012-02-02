.. index:: database

.. _creatingmatviews-chapter:

Creating a New Matview
======================

A materialized view, or "matview" is the results of a query stored as a table in the PostgreSQL database.  Matviews make user interfaces much more responsive by eliminating searches over many GB or sparse data at request time.  The majority of the time, new matviews will have the following characteristics:

* they will pull data from reports_clean and/or reports_user_info
* they will be updated once per day and store daily summary data
* they will be updated by a cron job calling a stored procedure

The rest of this guide assumes that all three conditions above are true.  For matviews for which one or more conditions are not true, consult the PostgreSQL DBAs for your matview.

Do I Want a Matview?
====================

Before proceeding to construct a new matview, test the responsiveness of simply running a query over reports_clean and/or reports_user_info.  You may find that the query returns fast enough ( < 100ms ) without its own matview.  Remember to test the extreme cases: Firefox release version on Windows, or Fennec aurora version. 

Also, matviews are really only effective if they are smaller than 1/4 the size of the base data from which they are constructed.   Otherwise, it's generally better to simply look at adding new indexes to the base data.  Try populating a couple days of the matview, ad-hoc, and checking its size (pg_total_relation_size()) compared to the base table from which it's drawn.  The new signature summaries was a good example of this; the matviews to meet the spec would have been 1/3 the size of reports_clean, so we added a couple new indexes to reports_clean instead.

Components of a Matview
=======================

In order to create a new matview, you will create or modify five or six things:

1. a table to hold the matview data
2. an update function to insert new matview data once per day
3. a backfill function to backfill one day of the matview
4. add a line in the general backfill_matviews function
5. if the matview is to be backfilled from deployment, a script to do this
6. a test that the matview is being populated correctly.

Point (6) is not yet addressed by a test framework for Socorro, so we're skipping it currently.

For the rest of this doc, please refer to the template matview code sql/templates/general_matview_template.sql in the Socorro source code.

Creating the Matview Table
==========================

The matview table should be the basis for the report or screen you want.  It's important that it be able to cope with all of the different filter and grouping criteria which users are allowed to supply.  On the other hand, most of the time it's not helpful to try to have one matview support several different reports; the matview gets bloated and slow.

In general, each matview will have the following things:

* one or more grouping columns
* a report_date column
* one or more summary data columns

If they are available, all columns should use surrogate keys to lookup lists (i.e. use signature_id, not the full text of the signature).  Generally the primary key of the matview will be the combination of all grouping columns plus the report date.

So, as an example, we're going to create a simple matview for summarizing crashes per product, web domain.  While it's unlikely that such a matview would be useful in practice (we could just query reports_clean directly) it makes a good example.   Here's the model for the table:

::

	table product_domain_counts
		product_version
		domain
		report_date
		report_count
		key product_version, domain, report_date
	
We actually use the custom procedure create_table_if_not_exists() to create this.  This function handles idempotence, permissions, and secondary indexes for us, like so:

::

	SELECT create_table_if_not_exists('product_domain_counts'
		$x$
		CREATE TABLE product_domain_counts (
			product_version_id INT NOT NULL,
			domain_id INT NOT NULL,
			report_date DATE NOT NULL,
			report_count INT NOT NULL DEFAULT 0,
			constraint product_domain_counts_key (
				product_version_id, domain_id, report_date )
			);
		$x$, 
		'breakpad_rw', ARRAY['domain_id'] );
		
See DatabaseAdminFunctions in the docs for more information about the function.

You'll notice that the resulting matview uses the surrogate keys of the corresponsing lookup lists rather than the actual values.  This is to keep matview sizes down and improve performance.  You'll also notice that there are no foriegn keys to the various lookup list tables; this is partly a performance optimization, but mostly because, since matviews are populated by stored procedure, validating input is not critical.  We also don't expect to need cascading updates or deletes on the lookup lists.

Creating The Update Function
----------------------------

Once you have the table, you'll need to write a function to be called by cron once per day in order to populate the matview with new data.  

This function will:

* be named update_{name_of_matview}
* take two parameters, a date and a boolean
* return a boolean, with true = success and ERROR = failure
* check if data it depends on is available
* check if it's already been run for the day
* pull its data from reports_clean, reports_user_info, and/or other matviews (_not_ reports or other raw data tables)

So, here's our update function for the product_domains table:

::

	CREATE OR REPLACE FUNCTION update_product_domain_counts (
		updateday DATE, checkdata BOOLEAN default TRUE )
	RETURNS BOOLEAN
	LANGUAGE plpgsql
	SET work_mem = '512MB'
	SET temp_buffers = '512MB'
	SET client_min_messages = 'ERROR'
	AS $f$
	BEGIN
	-- this function populates a daily matview
	-- for crash counts by product and domain
	-- depends on reports_clean
	
	-- check if we've been run
	IF checkdata THEN
		PERFORM 1 FROM product_domain_counts
		WHERE report_date = updateday
		LIMIT 1;
		IF FOUND THEN
			RAISE EXCEPTION 'product_domain_counts has already been run for %.',updateday;
		END IF;
	END IF;
	
	-- check if reports_clean is complete
	IF NOT reports_clean_done(updateday) THEN
		IF checkdata THEN
			RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
		ELSE
			RETURN TRUE;
		END IF;
	END IF;
	
	-- now insert the new records
	-- this should be some appropriate query, this simple group by
	-- is just provided as an example
	INSERT INTO product_domain_counts 
		( product_version_id, domain_id, report_date, report_count )
	SELECT product_version_id, domain_id,
		updateday,
		count(*)
	FROM reports_clean
	WHERE domain_id IS NOT NULL
		AND date_processed >= updateday::timestamptz
		AND date_processed < ( updateday + 1 )::timestamptz
	GROUP BY product_version_id, domain_id;
	
	RETURN TRUE;
	END; $f$;
	
Note that the update functions could be written in PL/python if you wish; however, there isn't yet a template for that.

Creating The Backfill Function
------------------------------

The second function which needs to be created is one for backfilling data
for specific dates, for when we need to backfill missing or corrected data.
This function will also be used to fill in data when we first deploy
the matview.

The backfill function will generally be very simple; it just calls
a delete for the days data and then the update function, with the
"checkdata" flag disabled:

::

	CREATE OR REPLACE FUNCTION backfill_product_domain_counts(
		updateday DATE )
	RETURNS BOOLEAN
	LANGUAGE plpgsql AS
	$f$
	BEGIN
	
	DELETE FROM product_domain_counts WHERE report_date = updateday;
	PERFORM update_product_domain_counts(updateday, false);
	
	RETURN TRUE;
	END; $f$;


Adding The Function To The Omnibus Backfill
-------------------------------------------

Usually when we backfill data we recreate all matview data for
the period affected.  This is accomplished by inserting it into
the backfill_matviews table:

::

	INSERT INTO backfill_matviews ( matview, function_name, frequency )
	VALUES ( 'product_domain_counts', 'backfill_product_domain_counts', 'daily' );
	
NOTE: the above is not yet active.  Until it is, send a request to Josh Berkus to add your new backfill to the omnibus backfill function.

Filling in Initial Data
-----------------------

Generally when creating a new matview, we want to fill in 
two weeks or so of data.  This can be done with either a Python 
or a PL/pgSQL script.  A PL/pgSQL script would be created as a SQL
file and look like this:

::

	DO $f$
	DECLARE 
		thisday DATE := '2012-01-14';
		lastday DATE;
	BEGIN
	
		-- set backfill to the last day we have ADU for
		SELECT max("date") 
		INTO lastday
		FROM raw_adu;
		
		WHILE thisday <= lastday LOOP
		
			RAISE INFO 'backfilling %', thisday;
		
			PERFORM backfill_product_domain_counts(thisday);
			
			thisday := thisday + 1;
			
		END LOOP;
		
	END;$f$;
	
This script would then be checked into the set of upgrade scripts 
for that version of the database.
		

















