CREATE OR REPLACE FUNCTION truncate_partitions(
    weeks_to_keep INTEGER
) RETURNS boolean
    LANGUAGE plpgsql
    AS $_X$
DECLARE
    tabname TEXT;
    mastername TEXT;
    basenames TEXT;
    listnames TEXT;
    cutoffdate DATE;
    safety_weeks TEXT;
BEGIN

IF weeks_to_keep < 1 THEN
    RAISE NOTICE 'Must specify more than 1 week of data to keep';
    RETURN FALSE;
END IF;

-- Casting weeks_to_keep to weeks for safety
safety_weeks := weeks_to_keep::text || ' weeks'; 

SELECT into cutoffdate (now() - safety_weeks::interval)::date;

-- Currently only truncating raw_crashes and processed_crashes
basenames := $q$SELECT table_name FROM report_partition_info
        WHERE partition_column = 'date_processed'
        AND table_name IN ('raw_crashes', 'processed_crashes')
        order by build_order desc$q$;

for mastername IN EXECUTE basenames LOOP

    -- Dig into our table list and pull out partitions matching
    -- our cutoffdate
    listnames := $q$SELECT relname FROM pg_stat_user_tables
        WHERE relname LIKE '$q$ || mastername || $q$_%'
        AND relname < '$q$ || mastername || '_'
        || to_char(cutoffdate, 'YYYYMMDD') || $q$'$q$;

    -- Lock the table and then truncate it
    FOR tabname IN EXECUTE listnames LOOP
        IF try_lock_table(tabname,'ACCESS EXCLUSIVE') THEN
            EXECUTE 'TRUNCATE TABLE ' || tabname;
        ELSE
            RAISE NOTICE 'Unable to lock table %; try again later', tabname;
            RETURN FALSE;
        END IF;
    END LOOP;
END LOOP;

RETURN TRUE;
END;
$_X$;
