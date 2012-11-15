\set ON_ERROR_STOP 1

BEGIN;

CREATE OR REPLACE FUNCTION backfill_crashes_by_user(
    updateday DATE, check_period INTERVAL DEFAULT INTERVAL '1 hour' )
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$function$
BEGIN

DELETE FROM crashes_by_user WHERE report_date = updateday;
PERFORM update_crashes_by_user(updateday, false, check_period);

RETURN TRUE;
END; $function$
;


COMMIT;
