CREATE OR REPLACE FUNCTION drop_old_partitions(
    mastername text,
    cutoffdate date
) RETURNS boolean
    LANGUAGE plpgsql
    AS $_X$
DECLARE
    tabname TEXT;
    listnames TEXT;
    safetydate DATE;
BEGIN

SELECT into safetydate (now() - '12 months'::interval)::date;

-- Do not run if date is within 12 mo
IF cutoffdate > safetydate THEN
    RAISE NOTICE 'Unable to remove paritions within 1 year of today';
    RETURN FALSE;
END IF;

listnames := $q$SELECT relname FROM pg_stat_user_tables
    WHERE relname LIKE '$q$ || mastername || $q$_%'
    AND relname < '$q$ || mastername || '_'
    || to_char(cutoffdate, 'YYYYMMDD') || $q$'$q$;

FOR tabname IN EXECUTE listnames LOOP
    IF try_lock_table(tabname,'ACCESS EXCLUSIVE') THEN
        EXECUTE 'DROP TABLE ' || tabname;
    ELSE
        RAISE NOTICE 'Unable to lock table %; try again later', tabname;
        RETURN FALSE;
    END IF;
END LOOP;

RETURN TRUE;
END;
$_X$;


