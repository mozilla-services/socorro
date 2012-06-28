\set ON_ERROR_STOP 1

BEGIN;

DROP VIEW IF EXISTS product_crash_ratio;

CREATE OR REPLACE VIEW product_crash_ratio AS
SELECT crcounts.product_version_id, product_versions.product_name,
    version_string, report_date as adu_date,
	sum(report_count) as crashes, sum(adu) as adu_count, throttle::numeric(5,2),
	sum(crashes/throttle)::int as adjusted_crashes,
	crash_hadu(sum(crashes), sum(adu), throttle) as crash_ratio
FROM crashes_by_user as crcounts
	JOIN crash_types USING (crash_type_id)
	JOIN product_versions ON crcounts.product_version_id = product_versions.product_version_id
	JOIN product_release_channels
		ON product_versions.product_name = product_release_channels.product_name
		AND product_versions.build_type = product_release_channels.release_channel
WHERE crash_type <> 'Hang Browser'
GROUP BY crcounts.product_version_id, product_versions.product_name,
    version_string, report_date, throttle;

ALTER VIEW product_crash_ratio OWNER TO breakpad_rw;
GRANT SELECT ON product_crash_ratio TO analyst;

DROP VIEW IF EXISTS product_os_crash_ratio;

CREATE OR REPLACE VIEW product_os_crash_ratio AS
SELECT crcounts.product_version_id, product_versions.product_name,
    version_string, os_names.os_short_name, os_names.os_name, report_date as adu_date,
	sum(report_count) as crashes, sum(adu) as adu_count, throttle::numeric(5,2),
	sum(crashes/throttle)::int as adjusted_crashes,
	crash_hadu(sum(crashes), sum(adu), throttle) as crash_ratio
FROM crashes_by_user AS crcounts
	JOIN crash_types USING (crash_type_id)
	JOIN product_versions ON crcounts.product_version_id = product_versions.product_version_id
	JOIN os_names ON crcounts.os_short_name::citext = os_names.os_short_name
	JOIN product_release_channels ON product_versions.product_name
		= product_release_channels.product_name
		AND product_versions.build_type = product_release_channels.release_channel
WHERE crash_type <> 'Hang Browser'
GROUP BY crcounts.product_version_id, product_versions.product_name,
    version_string, os_name, os_short_name, report_date, throttle;;

ALTER VIEW product_os_crash_ratio OWNER TO breakpad_rw;
GRANT SELECT ON product_os_crash_ratio TO analyst;