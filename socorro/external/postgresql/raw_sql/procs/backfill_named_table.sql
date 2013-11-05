CREATE OR REPLACE FUNCTION backfill_named_table(tablename text, updateday date) 
    RETURNS boolean
    LANGUAGE plpgsql
AS $function$
DECLARE
    update_proc_name TEXT := 'update_' || tablename;
BEGIN

-- Check if requested table for backfilling exists
PERFORM 1 FROM information_schema.tables WHERE table_name=tablename;
IF NOT FOUND THEN
    RAISE INFO 'table: % not found', tablename;
    RETURN FALSE;
END IF;

-- Check that requested function for update exists
PERFORM 1 FROM pg_proc WHERE proname = update_proc_name;
IF NOT FOUND THEN
    RAISE INFO 'proc: % not found', update_proc_name;
    RETURN FALSE;
END IF;

EXECUTE format('DELETE FROM %I WHERE report_date = %L', tablename, updateday);

EXECUTE format('SELECT %I(%L, FALSE)', update_proc_name, updateday);

RETURN TRUE;

END;
$function$
;
