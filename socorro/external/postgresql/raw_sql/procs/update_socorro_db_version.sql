CREATE OR REPLACE FUNCTION update_socorro_db_version(newversion text, backfilldate date DEFAULT NULL::date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE rerun BOOLEAN;
BEGIN
	SELECT current_version = newversion
	INTO rerun
	FROM socorro_db_version;
	
	IF rerun THEN
		RAISE NOTICE 'This database is already set to version %.  If you have deliberately rerun the upgrade scripts, then this is as expected.  If not, then there is something wrong.',newversion;
	ELSE
		UPDATE socorro_db_version SET current_version = newversion;
	END IF;
	
	INSERT INTO socorro_db_version_history ( version, upgraded_on, backfill_to )
		VALUES ( newversion, now(), backfilldate );
	
	RETURN true;
END; $$;


