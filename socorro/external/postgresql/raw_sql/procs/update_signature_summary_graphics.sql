CREATE OR REPLACE FUNCTION update_signature_summary_graphics(updateday date, checkdata boolean DEFAULT True)
    RETURNS BOOLEAN
    LANGUAGE plpgsql
-- common options:  IMMUTABLE  STABLE  STRICT  SECURITY DEFINER
AS $function$

BEGIN

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM signature_summary_graphics WHERE report_date = updateday LIMIT 1;
    IF FOUND THEN
        RAISE INFO 'signature_summary_graphics has already been run for %.',updateday;
    END IF;
END IF;

-- tables needed:
-- reports_clean
-- raw_crashes
-- product_versions

INSERT INTO signature_summary_graphics (
    report_date
    , signature_id
    , graphics_device_id
    , report_count
    , product_name
    , version_string
    , product_version_id
)
WITH graphics_info AS (
    SELECT
        reports_clean.signature_id as signature_id
        , json_object_field_text(raw_crash, 'AdapterVendorID') as vendor_hex
        , json_object_field_text(raw_crash, 'AdapterDeviceID') as adapter_hex
        , product_versions.product_name AS product_name
        , product_versions.product_version_id AS product_version_id
        , product_versions.version_string as version_string
    FROM raw_crashes
        JOIN reports_clean ON raw_crashes.uuid::text = reports_clean.uuid
        JOIN product_versions ON reports_clean.product_version_id = product_versions.product_version_id
    WHERE
        raw_crashes.date_processed::date = updateday
        AND reports_clean.date_processed::date = updateday
)
SELECT
    updateday as report_date
    , signature_id
    , graphics_device_id
    , count(graphics_device_id) as report_count
    , product_name
    , version_string
    , product_version_id
FROM
    graphics_info
    JOIN graphics_device ON
        graphics_info.vendor_hex = graphics_device.vendor_hex
        AND graphics_info.adapter_hex = graphics_device.adapter_hex
GROUP BY
    report_date, signature_id, graphics_device_id, product_name, product_version_id, version_string
;

RETURN TRUE;

END;

$function$
;
