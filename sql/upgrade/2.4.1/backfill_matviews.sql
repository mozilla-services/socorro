/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

DROP FUNCTION backfill_matviews ( date, text, date, boolean);

\set ON_ERROR_STOP 1

-- drop unneeded reports_clean function

DROP FUNCTION IF EXISTS backfill_reports_clean_by_date(date, date);

-- fix exception issue with backfill_adu

CREATE OR REPLACE FUNCTION backfill_adu (
	updateday date )
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $f$
BEGIN
-- stored procudure to delete and replace one day of
-- product_adu, optionally only for a specific product
-- intended to be called by backfill_matviews

DELETE FROM product_adu 
WHERE adu_date = updateday;

PERFORM update_adu(updateday, false);

RETURN TRUE;
END; $f$;


-- backfill function

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

-- set start date for r_c
first_rc := firstday AT TIME ZONE 'UTC';

-- check parameters
IF firstday > current_date OR lastday > current_date THEN
	RAISE EXCEPTION 'date parameter error: cannot backfill into the future';
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
