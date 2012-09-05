\set ON_ERROR_STOP 1

-- now create a backfill function
-- so that we can backfill missing data
CREATE OR REPLACE FUNCTION backfill_explosiveness(
	updateday DATE )
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$f$
BEGIN

PERFORM update_explosiveness(updateday, false);
DROP TABLE IF EXISTS crash_madu;
DROP TABLE IF EXISTS xtab_mult;
DROP TABLE IF EXISTS crash_xtab;
DROP TABLE IF EXISTS explosive_oneday;
DROP TABLE IF EXISTS explosive_threeday;

RETURN TRUE;
END; $f$;
