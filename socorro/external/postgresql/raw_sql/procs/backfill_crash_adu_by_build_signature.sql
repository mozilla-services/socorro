CREATE OR REPLACE FUNCTION backfill_crash_adu_by_build_signature(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- stored procedure to re-run graphics_device
-- intended to be called by backfill_matviews

PERFORM update_crash_adu_by_build_signature(updateday, false);

RETURN TRUE;
END; $$;
