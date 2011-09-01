\set ON_ERROR_STOP 1

-- function

CREATE OR REPLACE FUNCTION backfill_adu (
	firstday date, 
	forproduct text default '',
	lastday date default NULL, )
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $f$
DECLARE thisday DATE := firstday;
BEGIN
-- this producedure is meant to be called manually
-- by administrators in order to clear and backfill
-- the various matviews in order to recalculate old
-- data which was erroneous.
-- it requires a start date, and optionally takes
-- a product name and an end date

-- set optional end date
lastday := coalesce(last_day, current_date );

-- check parameters
IF firstday > current_date OR lastday > current_date or firstday > lastday THEN
	RAISE EXCEPTION 'date parameter error: cannot backfill into the future';
END IF;
IF forproduct <> '' THEN
	SELECT 1 FROM products WHERE product_name = forproduct;
	IF NOT FOUND THEN
		RAISE EXCEPTION 'product % does not exist or is misspelled',forproduct;
	END IF;
END IF;

-- loop through the days, backfilling one at a time
WHILE thisday <= lastday LOOP
	RAISE INFO 'backfilling for %',thisday;
	
	PERFORM backfill_adu(thisday, forproduct);
	
	PERFORM backfill_tcbs(thisday, forproduct);
	
	PERFORM backfill_daily_crashes(thisday, forproduct);
	
	thisday := thisday + 1;
	
END LOOP;

RETURN true;
END; $f$;
