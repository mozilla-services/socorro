CREATE OR REPLACE FUNCTION backfill_android_devices(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- stored procudure to re-run android_devices
-- intended to be called by backfill_matviews

PERFORM update_android_devices(updateday, false);

RETURN TRUE;
END; $$;

