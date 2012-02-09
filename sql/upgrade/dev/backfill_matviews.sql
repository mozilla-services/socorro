\set ON_ERROR_STOP 1

--create new matviews table for backfill
create_table_if_not_exists( 'backfill_matviews', $x$
	CREATE TABLE backfill_matviews (
		matview citext not null primary key,
		function_name citext not null
		frequency citext not null 
			check ( frequency IN ( 'hourly','daily','once-before','once-after' ) )
		run_order int not null default 99
		);
		
	INSERT INTO backfill_matviews
	VALUES ( 'tcbs', 'backfill_tcbs', 'daily', NULL,  1),
		( 'product_adu', 'backfill_adu', 'daily', NULL, 2),
		( 'daily_crashes', 'backfill_daily_crashes', 'daily', NULL, 3),
		( 'signatures', 'backfill_signatures', 'daily', NULL, 4 ),
		( 'hang_report', 'backfill_hang_report', 'daily', NULL, 5 ),
		( 'correlations', 'update_correlations', 'once-after', NULL, 1),
		( 'reports_duplicates', 'backfill_reports_duplicates', 'hourly', '3 hours', 1),
		( 'reports_clean', 'backfill_reports_clean', 'hourly', '3 hours', 2 )
		( 'product_versions', 'update_product_versions', 'once-before', NULL, 1);
	$x$,'breakpad_rw');



-- drop unneeded reports_clean function

DROP FUNCTION IF EXISTS backfill_matviews ( date, text, date, boolean);

-- backfill function

CREATE OR REPLACE FUNCTION backfill_matviews (
	firstday date,
	lastday date default NULL,
	run_hourlies boolean default true,
	matview_list text[] default '{}' )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET timezone = 'UTC'
AS $f$
DECLARE thisday DATE := firstday;
	last_hour timestamptz;
	first_rc timestamptz;
	last_adu DATE;
	hourly_lag INTERVAL := '3 hours';
	ignore_list boolean true;
	cur_mv CITEXT;
	cur_func CITEXT;
BEGIN
-- this producedure is meant to be called manually
-- by administrators in order to clear and backfill
-- the various matviews in order to recalculate old
-- data which was erroneous.
-- it requires a start date, and optionally an end date
-- no longer takes a product parameter
-- optionally disable hourly backfills
-- since those takes a long time

-- set start date for r_c
first_rc := firstday AT TIME ZONE 'UTC';

-- check parameters
IF firstday > current_date OR lastday > current_date THEN
	RAISE EXCEPTION 'date parameter error: cannot backfill into the future';
END IF;

-- set optional end date
IF lastday IS NULL or lastday = current_date THEN
	last_hour := date_trunc('hour', now()) - INTERVAL '3 hours'; 
ELSE 
	last_hour := ( lastday + 1 ) AT TIME ZONE 'UTC';
END IF;

-- check if lastday is after we have ADU;
-- if so, adjust lastday
SELECT max("date") 
INTO last_adu
FROM raw_adu;

IF lastday > last_adu THEN
	RAISE INFO 'last day of backfill period is after final day of ADU.  adjusting last day to %',last_adu;
	lastday := last_adu;
END IF;

ignore_list := ( matview_list = '{}' );

-- run the run-once before backfills
FOR cur_mv, cur_func IN
	SELECT matview, function_name FROM backfill_matviews
	WHERE frequency = 'once-before' AND 
		( ignore_list OR matview = ANY matview_list )
	ORDER BY run_order LOOP
	
	EXECUTE 'SELECT ' || cur_func || '(' || to_char(lastday,'YYYY-MM-DD') 
		|| ')';
		
END LOOP;
	
--run the hourly backfills, if running
IF run_hourlies THEN 

	
-- 
PERFORM update_product_versions();

-- backfill reports_clean.  this takes a while
-- we provide a switch to disable it
IF reportsclean THEN
	RAISE INFO 'backfilling reports_clean';
	PERFORM backfill_reports_clean( first_rc, last_hour );
END IF;

-- loop through the days, backfilling one at a time
WHILE thisday <= lastday LOOP
	RAISE INFO 'backfilling other matviews for %',thisday;
	RAISE INFO 'adu';
	PERFORM backfill_adu(thisday);
	RAISE INFO 'tcbs';
	PERFORM backfill_tcbs(thisday);
	DROP TABLE IF EXISTS new_tcbs;
	RAISE INFO 'daily crashes';
	PERFORM backfill_daily_crashes(thisday);
	RAISE INFO 'signatures';
	PERFORM update_signatures(thisday, FALSE);
	DROP TABLE IF EXISTS new_signatures;
	RAISE INFO 'hang report';
	PERFORM backfill_hang_report(thisday);

	thisday := thisday + 1;

END LOOP;

-- finally rank_compare, which doesn't need to be filled in for each day
PERFORM backfill_rank_compare(lastday);

RETURN true;
END; $f$;

DROP FUNCTION IF EXISTS backfill_matviews(date, text, date, boolean);
