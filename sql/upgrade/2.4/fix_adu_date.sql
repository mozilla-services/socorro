\set ON_ERROR_STOP 1

DO $f$
DECLARE newtype TEXT;
BEGIN
-- check if the type has already been changed
SELECT pg_typeof("date") 
INTO newtype
FROM raw_adu;

IF newtype <> 'date' THEN

	ALTER TABLE raw_adu ALTER COLUMN "date" TYPE date;
	
END IF;

END;$f$;

-- finally, analyze the whole database
-- this takes a while
ANALYSE VERBOSE;

