CREATE FUNCTION backfill_crashes_by_user_build(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM crashes_by_user_build WHERE report_date = updateday;
PERFORM update_crashes_by_user_build(updateday, false, check_period);

RETURN TRUE;
END; $$;


