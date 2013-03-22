CREATE FUNCTION backfill_daily_crashes(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- VERSION 4
-- deletes and replaces daily_crashes for selected dates
-- now just nests a call to update_daily_crashes

DELETE FROM daily_crashes
WHERE adu_day = updateday;
PERFORM update_daily_crashes(updateday, false);

RETURN TRUE;

END;$$;


