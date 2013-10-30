CREATE OR REPLACE FUNCTION backfill_signature_summary_graphics(updateday date)
    RETURNS boolean
    LANGUAGE plpgsql
    AS $function$
BEGIN

-- Deletes and replaces signature_summary for selected date

DELETE FROM signature_summary_graphics
WHERE report_date = updateday;

PERFORM update_signature_summary_graphics(updateday, false);

RETURN TRUE;

END;
$function$;
