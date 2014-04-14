CREATE OR REPLACE FUNCTION update_signature_summary_products(updateday date, checkdata boolean DEFAULT True)
 RETURNS boolean
 LANGUAGE plpgsql
 SET client_min_messages to 'ERROR'
 -- common options:  IMMUTABLE  STABLE  STRICT  SECURITY DEFINER
AS $function$

BEGIN

IF checkdata THEN
    PERFORM 1 FROM signature_summary_products WHERE report_date = updateday LIMIT 1;
    IF FOUND THEN
        RAISE INFO 'signature_summary_products has already been run for %.',updateday;
    END IF;
END IF;

INSERT INTO signature_summary_products (
    signature_id
    , product_version_id
    , product_name
    , version_string
    , report_count
    , report_date
)
SELECT
    signature_id
    , product_version_id
    , product_name
    , version_string
    , count(*) AS report_count
    , updateday AS report_date
FROM reports_clean
    JOIN product_versions USING (product_version_id)
WHERE
    utc_day_is(date_processed, updateday)
GROUP BY
    product_version_id
    , product_name
    , version_string
    , signature_id
    , updateday
;

RETURN TRUE;

END;

$function$
;
