CREATE OR REPLACE FUNCTION backfill_gccrashes(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- function for administrative backfilling of gccrashes
-- designed to be called by backfill_matviews
DELETE FROM gccrashes WHERE report_date = updateday;
PERFORM update_gccrashes(updateday, false, check_period);

RETURN TRUE;
END;$$;


