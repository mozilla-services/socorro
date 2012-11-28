\set ON_ERROR_STOP 1

BEGIN;

CREATE OR REPLACE FUNCTION public.backfill_daily_crashes(updateday date)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
BEGIN
-- VERSION 4
-- deletes and replaces daily_crashes for selected dates
-- now just nests a call to update_daily_crashes

DELETE FROM daily_crashes
WHERE adu_day = updateday;
PERFORM update_daily_crashes(updateday, false);

RETURN TRUE;

END;$function$
;

COMMIT;
