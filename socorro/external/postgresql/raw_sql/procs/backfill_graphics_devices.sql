CREATE OR REPLACE FUNCTION backfill_graphics_devices(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- stored procedure to re-run graphics_device
-- intended to be called by backfill_matviews

PERFORM update_graphics_devices(updateday, false);

RETURN TRUE;
END; $$;
