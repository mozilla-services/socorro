CREATE OR REPLACE FUNCTION update_signature_summary_devices(updateday date, checkdata boolean DEFAULT True)
    RETURNS BOOLEAN
    LANGUAGE plpgsql
-- common options:  IMMUTABLE  STABLE  STRICT  SECURITY DEFINER
AS $function$

BEGIN

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM signature_summary_device WHERE report_date = updateday LIMIT 1;
    IF FOUND THEN
        RAISE INFO 'signature_summary has already been run for %.',updateday;
    END IF;
END IF;

-- tables needed:
-- reports_clean
-- raw_crashes
-- product_versions

INSERT into signature_summary_device (
    report_date
    , signature_id
    , android_device_id
    , report_count
    , product_name
    , product_version_id
    , version_string
)
WITH android_info AS (
    SELECT
        reports_clean.signature_id as signature_id
        , json_object_field_text(raw_crash, 'Android_CPU_ABI') as android_cpu_abi
        , json_object_field_text(raw_crash, 'Android_Manufacturer') as android_manufacturer
        , json_object_field_text(raw_crash, 'Android_Model') as android_model
        , json_object_field_text(raw_crash, 'Android_Version') as android_version
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
    , android_device_id
    , count(android_device_id) as report_count
    , product_name
    , product_version_id
    , version_string
FROM
    android_info
    JOIN android_devices ON
        android_info.android_cpu_abi = android_devices.android_cpu_abi
        AND android_info.android_manufacturer = android_devices.android_manufacturer
        AND android_info.android_model = android_devices.android_model
        AND android_info.android_version = android_devices.android_version
GROUP BY
    report_date, signature_id, android_device_id, product_name, product_version_id, version_string
;


RETURN TRUE;

END;

$function$
;
