\set ON_ERROR_STOP 1

DROP FUNCTION IF EXISTS backfill_tcbs(date);

CREATE OR REPLACE FUNCTION backfill_tcbs(
    updateday DATE, check_period INTERVAL DEFAULT INTERVAL '1 hour' )
	RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- function for administrative backfilling of TCBS
-- designed to be called by backfill_matviews
DELETE FROM tcbs WHERE report_date = updateday;
PERFORM update_tcbs(updateday, false, check_period);

RETURN TRUE;
END;$$;
