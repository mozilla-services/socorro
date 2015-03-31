CREATE OR REPLACE FUNCTION find_weekly_partition(
    this_date DATE,
    which_table TEXT
)
    RETURNS text
    LANGUAGE plpgsql
    SET "TimeZone" TO 'UTC'
AS $_$
-- this function is meant to be called internally
-- checks if the correct reports_clean or reports_user_info partition exists
-- otherwise it creates it
-- returns the name of the partition
DECLARE this_part text;
    begin_week text;
    end_week text;
    rc_indexes text[];
    dex int := 1;
BEGIN

this_part := which_table || '_' || to_char(date_trunc('week', this_date), 'YYYYMMDD');

PERFORM 1
FROM pg_stat_user_tables
WHERE relname = this_part;
IF FOUND THEN
    RETURN this_part;
ELSE 
    RAISE EXCEPTION 'Partition for date % for table % not found', this_date, which_table;
END IF;

END;
$_$;
