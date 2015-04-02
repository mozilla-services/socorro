CREATE OR REPLACE FUNCTION update_signature_summary_installations(updateday date, checkdata boolean DEFAULT True)
 RETURNS boolean
 LANGUAGE plpgsql
 SET client_min_messages to 'ERROR'
 -- common options:  IMMUTABLE  STABLE  STRICT  SECURITY DEFINER
AS $function$
DECLARE
    partition_name TEXT;

BEGIN

IF checkdata THEN
    PERFORM 1 FROM signature_summary_installations WHERE report_date = updateday LIMIT 1;
    IF FOUND THEN
        RAISE INFO 'signature_summary_installations has already been run for %.',updateday;
    END IF;
END IF;

partition_name := find_weekly_partition(updateday, 'signature_summary_installations');

EXECUTE format(
    'INSERT into %I (
        signature_id
        , product_name
        , version_string
        , crash_count
        , install_count
        , report_date
    )
    SELECT
        signature_id
        , product_name
        , version_string
        , COUNT(*) AS crash_count
        , COUNT(DISTINCT client_crash_date - install_age) as install_count
        , %L::date AS report_date
    FROM reports_clean
        JOIN product_versions USING (product_version_id)
    WHERE
        utc_day_is(date_processed, %L)
    GROUP BY
        product_name
        , version_string
        , signature_id
        , report_date
    ',
    partition_name, updateday, updateday
);

RETURN TRUE;

END;

$function$
;
