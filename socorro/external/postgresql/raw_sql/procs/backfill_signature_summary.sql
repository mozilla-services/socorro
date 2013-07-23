CREATE OR REPLACE FUNCTION backfill_signature_summary(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

-- Deletes and replaces signature_summary for selected date

DELETE FROM signature_summary_products
WHERE report_date = updateday;

DELETE FROM signature_summary_installations
WHERE report_date = updateday;

DELETE FROM signature_summary_uptime
WHERE report_date = updateday;

DELETE FROM signature_summary_os
WHERE report_date = updateday;

DELETE FROM signature_summary_process_type
WHERE report_date = updateday;

DELETE FROM signature_summary_architecture
WHERE report_date = updateday;

DELETE FROM signature_summary_flash_version
WHERE report_date = updateday;

PERFORM update_signature_summary(updateday, false);

RETURN TRUE;

END;$$;
