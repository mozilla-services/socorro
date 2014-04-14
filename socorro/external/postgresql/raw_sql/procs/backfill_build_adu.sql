CREATE OR REPLACE FUNCTION backfill_build_adu(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM build_adu WHERE adu_date = updateday;
PERFORM update_build_adu(updateday, false);

RETURN TRUE;
END; $$;


