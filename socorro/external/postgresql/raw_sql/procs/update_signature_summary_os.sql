CREATE OR REPLACE FUNCTION update_signature_summary_os(updateday date, checkdata boolean DEFAULT True)
    RETURNS BOOLEAN
    LANGUAGE plpgsql
-- common options:  IMMUTABLE  STABLE  STRICT  SECURITY DEFINER
AS $function$

BEGIN

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM signature_summary_os WHERE report_date = updateday LIMIT 1;
    IF FOUND THEN
        RAISE INFO 'signature_summary_os has already been run for %.',updateday;
    END IF;
END IF;

INSERT into signature_summary_os (
    os_version_string
    , signature_id
    , product_name
    , product_version_id
    , version_string
    , report_count
    , report_date
)
SELECT
    os_version_string
    , signature_id
    , product_versions.product_name AS product_name
    , product_versions.product_version_id AS product_version_id
    , product_versions.version_string AS version_string
    , count(*) AS report_count
    , updateday AS report_date
FROM reports_clean
    JOIN product_versions USING (product_version_id)
    JOIN os_versions USING (os_version_id)
WHERE
    utc_day_is(date_processed, updateday)
    AND os_version_string IS NOT NULL
GROUP BY
    os_version_string
    , signature_id
    , product_versions.product_name
    , product_versions.product_version_id
    , product_versions.version_string
    , report_date
;

RETURN TRUE;

END;

$function$
;
