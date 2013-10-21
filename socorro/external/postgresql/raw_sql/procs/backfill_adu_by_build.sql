CREATE OR REPLACE FUNCTION backfill_adu_by_build(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- stored procedure to re-run graphics_device
-- intended to be called by backfill_matviews

PERFORM update_adu_by_build(updateday, false);

RETURN TRUE;
END; $$;
