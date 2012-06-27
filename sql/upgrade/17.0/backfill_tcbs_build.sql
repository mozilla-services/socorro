\set ON_ERROR_STOP 1

CREATE FUNCTION backfill_tcbs_build(
    updateday DATE, check_period INTERVAL DEFAULT INTERVAL '1 hour' )
	RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- function for administrative backfilling of TCBS
-- designed to be called by backfill_matviews
DELETE FROM tcbs_build WHERE report_date = updateday;
PERFORM update_tcbs_build(updateday, false, check_period);

RETURN TRUE;
END;$$;
