CREATE FUNCTION backfill_explosiveness(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

PERFORM update_explosiveness(updateday, false);
DROP TABLE IF EXISTS crash_madu;
DROP TABLE IF EXISTS xtab_mult;
DROP TABLE IF EXISTS crash_xtab;
DROP TABLE IF EXISTS explosive_oneday;
DROP TABLE IF EXISTS explosive_threeday;

RETURN TRUE;
END; $$;


