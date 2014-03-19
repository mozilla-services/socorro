CREATE OR REPLACE FUNCTION drop_named_partitions(
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

listnames := $q$SELECT table_name FROM report_partition_info
        WHERE partition_column = 'date_processed'
        order by build_order desc$q$;

FOR tabname IN EXECUTE listnames LOOP
    EXECUTE 'SELECT drop_old_partitions($1, $2)' USING tabname, cutoffdate;
END LOOP;

RETURN TRUE;
END;
$_X$;


