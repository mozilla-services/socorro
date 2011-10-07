\set ON_ERROR_STOP 1

-- function

CREATE OR REPLACE FUNCTION backfill_hangreport (
	firstday date,
	lastday date default NULL )
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $f$
DECLARE thisday DATE := firstday;
BEGIN
-- this producedure is meant to be called manually
-- by administrators in order to backfill
-- the hang/crash report

-- set optional end date
lastday := coalesce(lastday, current_date );

-- check parameters
IF firstday > current_date OR lastday > current_date or firstday > lastday THEN
	RAISE EXCEPTION 'date parameter error: cannot backfill into the future';
END IF;

-- loop through the days, backfilling one at a time
WHILE thisday <= lastday LOOP
	RAISE INFO 'backfilling for %',thisday;
	PERFORM update_hang_report(thisday);
        
	thisday := thisday + 1;

END LOOP;

RETURN true;
END; $f$;
