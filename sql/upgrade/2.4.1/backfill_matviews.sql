DROP FUNCTION backfill_matviews ( date, text, date, boolean);

\set ON_ERROR_STOP 1

DROP FUNCTION IF EXISTS backfill_reports_clean_by_date(date, date);

-- function

CREATE OR REPLACE FUNCTION backfill_matviews (
	firstday date,
	lastday date default NULL,
	reportsclean boolean default true )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET timezone = 'UTC'
AS $f$
DECLARE thisday DATE := firstday;
	last_rc timestamptz;
	first_rc timestamptz;
BEGIN
-- this producedure is meant to be called manually
-- by administrators in order to clear and backfill
-- the various matviews in order to recalculate old
-- data which was erroneous.
-- it requires a start date, and optionally an end date
-- no longer takes a product parameter
-- optionally disable reports_clean backfill
-- since that takes a long time

-- set start date for r_c
first_rc := firstday AT TIME ZONE 'UTC';

-- set optional end date
IF lastday IS NULL THEN:
	lastday := current_date;
	last_rc := date_trunc('hour', now()) - INTERVAL '3 hours'; 
ELSE
	last_rc := ( lastday + 1 ) AT TIME ZONE 'UTC';
END IF;
	

-- check parameters
IF firstday > current_date OR lastday > current_date THEN
	RAISE EXCEPTION 'date parameter error: cannot backfill into the future';
END IF;

-- fill in products
PERFORM update_product_versions();

-- backfill reports_clean.  this takes a while
-- we provide a switch to disable it
IF reportsclean THEN
	RAISE INFO 'backfilling reports_clean';
	PERFORM backfill_reports_clean( first_rc, last_rc );
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

\set ON_ERROR_STOP 0

DROP FUNCTION backfill_matviews(date, text, date, boolean);
