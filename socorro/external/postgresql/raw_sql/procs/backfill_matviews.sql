CREATE OR REPLACE FUNCTION backfill_matviews(firstday date, lastday date DEFAULT NULL::date, reportsclean boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET "TimeZone" TO 'UTC'
    AS $$
DECLARE thisday DATE := firstday;
	last_rc timestamptz;
	first_rc timestamptz;
	last_adu DATE;
BEGIN
-- this producedure is meant to be called manually
-- by administrators in order to clear and backfill
-- the various matviews in order to recalculate old
-- data which was erroneous.
-- it requires a start date, and optionally an end date
-- no longer takes a product parameter
-- optionally disable reports_clean backfill
-- since that takes a long time

-- this is a temporary fix for matview backfill for mobeta
-- a more complete fix is coming in 19.0.

-- set start date for r_c
first_rc := firstday AT TIME ZONE 'UTC';

-- check parameters
IF firstday > current_date OR lastday > current_date THEN
	RAISE NOTICE 'date parameter error: cannot backfill into the future';
    RETURN FALSE;
END IF;

-- set optional end date
IF lastday IS NULL or lastday = current_date THEN
	last_rc := date_trunc('hour', now()) - INTERVAL '3 hours';
ELSE
	last_rc := ( lastday + 1 ) AT TIME ZONE 'UTC';
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
	PERFORM backfill_build_adu(thisday);
	RAISE INFO 'signatures';
	PERFORM update_signatures(thisday, FALSE);
	RAISE INFO 'tcbs';
	PERFORM backfill_tcbs(thisday, check_period);
	PERFORM backfill_tcbs_build(thisday);
	DROP TABLE IF EXISTS new_tcbs;
	RAISE INFO 'crashes by user';
	PERFORM backfill_crashes_by_user(thisday);
	PERFORM backfill_crashes_by_user_build(thisday);
	RAISE INFO 'home page graph';
	PERFORM backfill_home_page_graph(thisday);
	PERFORM backfill_home_page_graph_build(thisday);
	DROP TABLE IF EXISTS new_signatures;
	RAISE INFO 'hang report (slow)';
	PERFORM backfill_hang_report(thisday);
	RAISE INFO 'nightly builds';
	PERFORM backfill_nightly_builds(thisday);
	RAISE INFO 'exploitability';
	PERFORM backfill_exploitability(thisday);

	thisday := thisday + 1;

END LOOP;

-- finally rank_compare and correlations, which don't need to be filled in for each day
RAISE INFO 'rank_compare';
PERFORM backfill_rank_compare(lastday);
RAISE INFO 'explosiveness (slow)';
PERFORM backfill_explosiveness(thisday);
RAISE INFO 'correlations';
PERFORM backfill_correlations(lastday);

RETURN true;
END; $$;


