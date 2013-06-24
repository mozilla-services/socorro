/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
'**new_matview_name**', 
-- full SQL create table statement here
$q$
create table **new_matview_name** (
	**col1** DATATYPE not null,
	**col2** DATATYPE not null,
	report_date DATE not null,
	col3 DATATYPE not null,
	constraint **new_matview_name**_key primary key ( **col1**, **col2**, report_date )
);$q$, 
-- owner of table; always breakpad_rw
'breakpad_rw', 
-- array of indexes to create
ARRAY [ '**col1**,report_date', '**col2**' ]);


-- daily update function
CREATE OR REPLACE FUNCTION update_**new_matview_name** (
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
	PERFORM 1 FROM **new_matview_name**
	WHERE report_date = updateday
	LIMIT 1;
	IF FOUND THEN
		RAISE EXCEPTION '**new_matview_name** has already been run for %.',updateday;
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
INSERT INTO **new_matview_name** 
	( **col1**, **col2**, report_date, **col3** )
SELECT **col1**, **col2**,
	updateday,
	**AGGREGATE**(**col4**)
FROM reports_clean
WHERE **condition**
	AND date_processed >= updateday::timestamptz
	AND date_processed < ( updateday + 1 )::timestamptz
GROUP BY **col1**, **col2**;

RETURN TRUE;
END; $f$;

-- now create a backfill function 
-- so that we can backfill missing data
CREATE OR REPLACE FUNCTION backfill_**new_matview_name**(
	updateday DATE )
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$f$
BEGIN

DELETE FROM **new_matview_name** WHERE report_date = updateday;
PERFORM update_**new_matview_name**(updateday, false);

RETURN TRUE;
END; $f$;


-- sample backfill script
-- for initialization
DO $f$
DECLARE 
	thisday DATE := **first_day_of_backfill**;
	lastday DATE;
BEGIN

	-- set backfill to the last day we have ADU for
	SELECT max("date") 
	INTO lastday
	FROM raw_adu;
	
	WHILE thisday <= lastday LOOP
	
		RAISE INFO 'backfilling %', thisday;
	
		PERFORM backfill_**new_matview_name**(thisday);
		
		thisday := thisday + 1;
		
	END LOOP;
	
END;$f$;










