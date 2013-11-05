CREATE OR REPLACE FUNCTION update_signature_summary_architecture(updateday date, checkdata boolean DEFAULT True)
    RETURNS BOOLEAN
    LANGUAGE plpgsql
-- common options:  IMMUTABLE  STABLE  STRICT  SECURITY DEFINER
AS $function$

BEGIN

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM signature_summary_architecture WHERE report_date = updateday LIMIT 1;
    IF FOUND THEN
        RAISE INFO 'signature_summary_architecture has already been run for %.',updateday;
    END IF;
END IF;

INSERT into signature_summary_architecture (
    architecture
    , signature_id
    , product_name
    , product_version_id
    , version_string
    , report_date
    , report_count
)
SELECT
    architecture
    , signature_id
    , product_versions.product_name AS product_name
    , product_versions.product_version_id AS product_version_id
    , product_versions.version_string AS version_string
    , updateday AS report_date
    , count(*) AS report_count
FROM reports_clean
    JOIN product_versions USING (product_version_id)
WHERE
    utc_day_is(date_processed, updateday)
    AND architecture IS NOT NULL
GROUP BY
    architecture
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
