CREATE OR REPLACE FUNCTION update_signature_summary(updateday date, checkdata boolean DEFAULT True)
 RETURNS boolean
 LANGUAGE plpgsql
 SET client_min_messages to 'ERROR'
 -- common options:  IMMUTABLE  STABLE  STRICT  SECURITY DEFINER
AS $function$

-- Provide signature_summary_* matviews which provide signature-specific
-- rollups of interesting data

BEGIN

-- check if we've been run
IF checkdata THEN
	PERFORM 1 FROM signature_summary_products WHERE report_date = updateday LIMIT 1;
	IF FOUND THEN
		RAISE INFO 'signature_summary has already been run for %.',updateday;
	END IF;
END IF;

-- tables needed:
-- reports_clean
-- product_versions
-- os_versions
-- flash_versions

-- signature summary by products
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
    date_processed::date = updateday
GROUP BY product_version_id, product_name, version_string, signature_id, updateday
;

-- signature summary by distinct_install
INSERT into signature_summary_installations (
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
    , updateday AS report_date
FROM reports_clean
    JOIN product_versions USING (product_version_id)
WHERE
    date_processed::date = updateday
GROUP BY product_name, version_string, signature_id
;

-- uptime_string
INSERT into signature_summary_uptime (
    uptime_string
    , signature_id
    , product_name
    , product_version_id
    , version_string
    , report_count
    , report_date
)
SELECT
    uptime_string
    , signature_id
    , product_versions.product_name as product_name
    , product_versions.product_version_id as product_version_id
    , product_versions.version_string as version_string
    , count(*) AS report_count
    , updateday AS report_date
FROM reports_clean
    JOIN product_versions USING (product_version_id)
    JOIN uptime_levels ON
        reports_clean.uptime >= min_uptime AND
        reports_clean.uptime < max_uptime
WHERE
    date_processed::date = updateday
    AND uptime_string IS NOT NULL
GROUP BY
    uptime_string, signature_id, product_versions.product_name, product_versions.product_version_id, product_versions.version_string, report_date
;

-- os
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
    , product_versions.version_string as version_string
    , count(*) AS report_count
    , updateday AS report_date
FROM reports_clean
    JOIN product_versions USING (product_version_id)
    JOIN os_versions USING (os_version_id)
WHERE
    date_processed::date = updateday
    AND os_version_string IS NOT NULL
GROUP BY
    os_version_string, signature_id, product_versions.product_name, product_versions.product_version_id, product_versions.version_string, report_date
;

-- process_type
INSERT into signature_summary_process_type (
    process_type
    , signature_id
    , product_name
    , product_version_id
    , version_string
    , report_count
    , report_date
)
SELECT
    process_type
    , signature_id
    , product_versions.product_name AS product_name
    , product_versions.product_version_id AS product_version_id
    , product_versions.version_string as version_string
    , count(*) AS report_count
    , updateday AS report_date
FROM reports_clean
    JOIN product_versions USING (product_version_id)
WHERE
    date_processed::date = updateday
    AND process_type IS NOT NULL
GROUP BY
    process_type, signature_id, product_versions.product_name, product_versions.product_version_id, product_versions.version_string, report_date
;
-- architecture
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
    , product_versions.version_string as version_string
    , updateday AS report_date
    , count(*) AS report_count
FROM reports_clean
    JOIN product_versions USING (product_version_id)
WHERE
    date_processed::date = updateday
    AND architecture IS NOT NULL
GROUP BY
    architecture, signature_id, product_versions.product_name, product_versions.product_version_id, product_versions.version_string, report_date
;
-- flash_version
INSERT into signature_summary_flash_version (
    flash_version
    , signature_id
    , product_name
    , product_version_id
    , version_string
    , report_date
    , report_count
)
SELECT
    CASE WHEN flash_version = '' THEN 'Unknown/No Flash' ELSE flash_version END
    , signature_id
    , product_versions.product_name AS product_name
    , product_versions.product_version_id AS product_version_id
    , product_versions.version_string as version_string
    , updateday AS report_date
    , count(*) AS report_count
FROM reports_clean
    JOIN product_versions USING (product_version_id)
    LEFT OUTER JOIN flash_versions USING (flash_version_id)
WHERE
    date_processed::date = updateday
GROUP BY
    flash_version, signature_id, product_versions.product_name, product_versions.product_version_id, product_versions.version_string, report_date
;

INSERT into signature_summary_device (
    report_date
    , signature_id
    , android_device_id
    , report_count
)
WITH android_info AS (
    SELECT
        reports_clean.signature_id as signature_id
        , json_object_field_text(raw_crash, 'Android_CPU_ABI') as android_cpu_abi
        , json_object_field_text(raw_crash, 'Android_Manufacturer') as android_manufacturer
        , json_object_field_text(raw_crash, 'Android_Model') as android_model
        , json_object_field_text(raw_crash, 'Android_Version') as android_version
    FROM raw_crashes
        JOIN reports_clean ON raw_crashes.uuid::text = reports_clean.uuid
    WHERE
        raw_crashes.date_processed::date = updateday
        AND reports_clean.date_processed::date = updateday
)
SELECT
    updateday as report_date
    , signature_id
    , android_device_id
    , count(android_device_id) as report_count
FROM
    android_info
    JOIN android_devices ON
        android_info.android_cpu_abi = android_devices.android_cpu_abi
        AND android_info.android_manufacturer = android_devices.android_manufacturer
        AND android_info.android_model = android_devices.android_model
        AND android_info.android_version = android_devices.android_version
GROUP BY
    report_date, signature_id, android_device_id
;

RETURN TRUE;

END;
$function$
;
