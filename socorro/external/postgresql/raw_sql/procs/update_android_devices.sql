CREATE OR REPLACE FUNCTION update_android_devices(updateday date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET "TimeZone" TO 'UTC'
    AS $$
BEGIN

CREATE TEMPORARY TABLE new_android_devices
ON COMMIT DROP AS
    SELECT DISTINCT
        json_object_field_text(raw_crash, 'Android_CPU_ABI') as android_cpu_abi
        , json_object_field_text(raw_crash, 'Android_Manufacturer') as android_manufacturer
        , json_object_field_text(raw_crash, 'Android_Model') as android_model
        , json_object_field_text(raw_crash, 'Android_Version') as android_version
    FROM raw_crashes
    WHERE
        date_processed >= updateday
        AND date_processed <= (updateday + 1)
    GROUP BY
        android_cpu_abi
        , android_manufacturer
        , android_model
        , android_version
;

PERFORM 1 FROM new_android_devices;
IF NOT FOUND THEN
    IF checkdata THEN
        RAISE NOTICE 'no new android devices found in raw_crashes for date %',updateday;
        RETURN FALSE;
    END IF;
END IF;

ANALYZE new_android_devices;

-- update android_devices

INSERT INTO android_devices (
    android_cpu_abi
    , android_manufacturer
    , android_model
    , android_version
)
SELECT
    new_android_devices.android_cpu_abi
    , new_android_devices.android_manufacturer
    , new_android_devices.android_model
    , new_android_devices.android_version
FROM new_android_devices
LEFT OUTER JOIN android_devices
ON new_android_devices.android_cpu_abi = android_devices.android_cpu_abi
    AND new_android_devices.android_manufacturer = android_devices.android_manufacturer
    AND new_android_devices.android_model = android_devices.android_model
    AND new_android_devices.android_version = android_devices.android_version
GROUP BY
    new_android_devices.android_cpu_abi
    , new_android_devices.android_manufacturer
    , new_android_devices.android_model
    , new_android_devices.android_version
;

RETURN True;

END;
$$;
