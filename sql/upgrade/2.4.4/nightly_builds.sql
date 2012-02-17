\set ON_ERROR_STOP 1

-- what follows is a template for creating new matviews 
-- and their attendant mantenance procedures
-- replace all of the **dummy table and column names** below
-- as appropriate

-- this template assumes that:
-- a. the matview is a summary of data in reports_clean
-- b. the matview is grouped by day

SELECT create_table_if_not_exists ( 
-- new table name here
'nightly_builds', 
-- full SQL create table statement here
$q$
create table nightly_builds (
	product_version_id INT not null,
	build_date DATE not null,
	report_date DATE not null,
	days_out INT not null,
	report_count INT NOT NULL default 0,
	constraint nightly_builds_key primary key ( product_version_id, build_date, days_out )
);$q$, 
-- owner of table; always breakpad_rw
'breakpad_rw', 
-- array of indexes to create
ARRAY [ 'product_version_id,report_date']);


-- daily update function
CREATE OR REPLACE FUNCTION update_nightly_builds (
	updateday DATE, checkdata BOOLEAN default TRUE )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
SET client_min_messages = 'ERROR'
AS $f$
BEGIN
-- this function populates a daily matview
-- for **new_matview_description**
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
	PERFORM 1 FROM nightly_builds
	WHERE report_date = updateday
	LIMIT 1;
	IF FOUND THEN
		RAISE EXCEPTION 'nightly_builds has already been run for %.',updateday;
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
INSERT INTO nightly_builds (
	product_version_id, build_date, report_date,
	days_out, report_count )
SELECT product_version_id, 
	build_date(reports_clean.build) as build_date, 
	date_processed::date as report_date,
	date_processed::date 
		- build_date(reports_clean.build) as days_out,
	count(*)
FROM reports_clean
	join product_versions using (product_version_id)
	join product_version_builds using (product_version_id)
WHERE 
	reports_clean.build = product_version_builds.build_id
	and reports_clean.release_channel IN ( 'nightly', 'aurora' )
	and date_processed::date 
		- build_date(reports_clean.build) <= 14
	and tstz_between(date_processed, build_date, sunset_date)
	and utc_day_is(date_processed,updateday)
GROUP BY product_version_id, product_name, version_string,
	build_date(build), date_processed::date
ORDER BY product_version_id, build_date, days_out;

RETURN TRUE;
END; $f$;

-- now create a backfill function 
-- so that we can backfill missing data
CREATE OR REPLACE FUNCTION backfill_nightly_builds(
	updateday DATE )
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$f$
BEGIN

DELETE FROM nightly_builds WHERE report_date = updateday;
PERFORM update_nightly_builds(updateday, false);

RETURN TRUE;
END; $f$;


-- sample backfill script
-- for initialization
DO $f$
DECLARE 
	thisday DATE;
	lastday DATE;
BEGIN

	-- backfill 2 weeks
	thisday := current_date - 14;

	-- set backfill to the last day we have ADU for
	SELECT max("date") 
	INTO lastday
	FROM raw_adu;
	
	WHILE thisday <= lastday LOOP
	
		RAISE INFO 'backfilling %', thisday;
	
		PERFORM backfill_nightly_builds(thisday);
		
		thisday := thisday + 1;
		
	END LOOP;
	
END;$f$;










