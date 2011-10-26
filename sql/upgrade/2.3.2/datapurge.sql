CREATE OR REPLACE FUNCTION try_lock_table (
	tabname text, mode text default 'EXCLUSIVE', attempts int default 20 )
RETURNS boolean
LANGUAGE plpgsql
AS $f$
-- this function tries to lock a table
-- in a loop, retrying every 3 seconds for 20 tries
-- until it gets a lock
-- or gives up
-- returns true if the table is locked, false
-- if unable to lock
DECLARE loopno INT := 1;
BEGIN
	WHILE loopno < attempts LOOP
		BEGIN
			EXECUTE 'LOCK TABLE ' || tabname || ' IN ' || mode || ' MODE NOWAIT';
			RETURN TRUE;
		EXCEPTION
			WHEN LOCK_NOT_AVAILABLE THEN
				PERFORM pg_sleep(3);
				CONTINUE;
		END;
	END LOOP;
RETURN FALSE;
END;$f$;

DROP FUNCTION drop_old_partitions(text,numeric); 

CREATE OR REPLACE FUNCTION drop_old_partitions (
	mastername text, cutoffdate date )
RETURNS boolean
LANGUAGE plpgsql
AS
$f$
DECLARE tabname TEXT;
	listnames TEXT;
BEGIN
listnames := $q$SELECT relname FROM pg_stat_user_tables
		WHERE relname LIKE '$q$ || mastername || $q$_%' 
		AND relname < '$q$ || mastername || '_' 
		|| to_char(cutoffdate, 'YYYYMMDD') || $q$'$q$;

IF try_lock_table(mastername,'ACCESS EXCLUSIVE') THEN
	FOR tabname IN EXECUTE listnames LOOP
		
		EXECUTE 'DROP TABLE ' || tabname;
		
	END LOOP;
ELSE
	RAISE EXCEPTION 'Unable to lock table plugin_reports; try again later';
END IF;
RETURN TRUE;
END;
$f$;
