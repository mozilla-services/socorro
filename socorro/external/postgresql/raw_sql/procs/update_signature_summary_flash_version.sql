CREATE OR REPLACE FUNCTION update_signature_summary_flash_version(updateday date, checkdata boolean DEFAULT True)
    RETURNS BOOLEAN
    LANGUAGE plpgsql
-- common options:  IMMUTABLE  STABLE  STRICT  SECURITY DEFINER
AS $function$
DECLARE
    partition_name TEXT;

BEGIN

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM signature_summary_flash_version WHERE report_date = updateday LIMIT 1;
    IF FOUND THEN
        RAISE INFO 'signature_summary_flash_version has already been run for %.',updateday;
    END IF;
END IF;

partition_name := find_weekly_partition(updateday, 'signature_summary_flash_version');

EXECUTE format(
    'INSERT into %I (
        flash_version
        , signature_id
        , product_name
        , product_version_id
        , version_string
        , report_date
        , report_count
    )
    SELECT
        CASE WHEN flash_version = '''' THEN ''Unknown/No Flash'' ELSE flash_version END
        , signature_id
        , product_versions.product_name AS product_name
        , product_versions.product_version_id AS product_version_id
        , product_versions.version_string as version_string
        , %L::date AS report_date
        , count(*) AS report_count
    FROM reports_clean
        JOIN product_versions USING (product_version_id)
        LEFT OUTER JOIN flash_versions USING (flash_version_id)
    WHERE
        utc_day_is(date_processed, %L)
    GROUP BY
        flash_version
        , signature_id
        , product_versions.product_name
        , product_versions.product_version_id
        , product_versions.version_string
        , report_date
    ',
    partition_name, updateday, updateday
);

RETURN TRUE;

END;
$function$
;
