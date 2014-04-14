CREATE OR REPLACE FUNCTION backfill_tcbs_build(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- function for administrative backfilling of TCBS
-- designed to be called by backfill_matviews
DELETE FROM tcbs_build WHERE report_date = updateday;
PERFORM update_tcbs_build(updateday, false, check_period);

RETURN TRUE;
END;$$;


