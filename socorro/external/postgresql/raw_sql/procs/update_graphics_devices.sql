CREATE OR REPLACE FUNCTION update_graphics_devices(updateday date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET "TimeZone" to 'UTC'
    AS $$
BEGIN

CREATE TEMPORARY TABLE new_graphics_devices
AS
    SELECT DISTINCT
        json_object_field_text(raw_crash, 'AdapterVendorID') as vendor_hex
        , json_object_field_text(raw_crash, 'AdapterDeviceID') as adapter_hex
    FROM raw_crashes
    WHERE
        date_processed >= updateday
        AND date_processed <= (updateday + 1)
    GROUP BY
        vendor_hex
        , adapter_hex
;

PERFORM 1 FROM new_graphics_devices;
IF NOT FOUND THEN
    IF checkdata THEN
        RAISE NOTICE 'no new vendor/adapter hexes found in raw_crashes for day %',updateday;
        RETURN FALSE;
    END IF;
END IF;

ANALYZE new_graphics_devices;

-- update graphics_device;

INSERT INTO graphics_device (
    vendor_hex
    , adapter_hex
)
SELECT
    new_graphics_devices.vendor_hex
    , new_graphics_devices.adapter_hex
FROM new_graphics_devices
LEFT OUTER JOIN graphics_device
ON new_graphics_devices.vendor_hex = graphics_device.vendor_hex
    AND new_graphics_devices.adapter_hex = graphics_device.adapter_hex
WHERE graphics_device.graphics_device_id IS NULL
AND new_graphics_devices.vendor_hex IS NOT NULL
GROUP BY
    new_graphics_devices.vendor_hex
    , new_graphics_devices.adapter_hex
;

DROP TABLE new_graphics_devices;

RETURN True;

END;
$$;
