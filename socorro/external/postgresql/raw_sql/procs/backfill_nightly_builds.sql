CREATE FUNCTION backfill_nightly_builds(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM nightly_builds WHERE report_date = updateday;
PERFORM update_nightly_builds(updateday, false);

RETURN TRUE;
END; $$;


