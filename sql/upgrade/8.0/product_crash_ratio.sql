\set ON_ERROR_STOP 1

CREATE OR REPLACE VIEW product_crash_ratio AS
WITH crcounts AS (
	SELECT productdims_id AS product_version_id,
		sum("count") as crashes,
		adu_day as report_date
	FROM daily_crashes 
	WHERE report_type IN ('C', 'p', 'T', 'P')
		AND "count" > 0
	GROUP BY productdims_id, adu_day
),
adusum AS (
	SELECT product_version_id, adu_date, sum(adu_count) as adu_count
	FROM product_adu
	GROUP BY product_version_id, adu_date )
SELECT crcounts.product_version_id, product_versions.product_name,
    version_string, adu_date,
	crashes, adu_count, throttle::numeric(5,2),
	(crashes/throttle)::int as adjusted_crashes, 
	(((crashes/throttle) * 100 ) / adu_count )::numeric(12,3) as crash_ratio
FROM crcounts
	JOIN product_versions ON crcounts.product_version_id = product_versions.product_version_id
	JOIN adusum ON crcounts.report_date = adusum.adu_date
		AND crcounts.product_version_id = adusum.product_version_id
	JOIN product_release_channels ON product_versions.product_name 
		= product_release_channels.product_name
		AND product_versions.build_type = product_release_channels.release_channel;
		
ALTER VIEW product_crash_ratio OWNER TO breakpad_rw;
GRANT SELECT ON product_crash_ratio TO analyst;

CREATE OR REPLACE VIEW product_os_crash_ratio AS
WITH crcounts AS (
	SELECT productdims_id AS product_version_id,
		os_short_name,
		sum("count") as crashes,
		adu_day as report_date
	FROM daily_crashes 
	WHERE report_type IN ('C', 'p', 'T', 'P')
		AND "count" > 0
	GROUP BY productdims_id, adu_day, os_short_name
)
SELECT crcounts.product_version_id, product_versions.product_name,
    version_string, os_names.os_short_name, os_names.os_name, adu_date,
	crashes, adu_count, throttle::numeric(5,2),
	(crashes/throttle)::int as adjusted_crashes, 
	(((crashes/throttle) * 100 ) / adu_count )::numeric(12,3) as crash_ratio
FROM crcounts
	JOIN product_versions ON crcounts.product_version_id = product_versions.product_version_id
	JOIN os_names ON crcounts.os_short_name::citext = os_names.os_short_name
	JOIN product_adu ON crcounts.report_date = product_adu.adu_date
		AND crcounts.product_version_id = product_adu.product_version_id
		AND product_adu.os_name::citext = os_names.os_name
	JOIN product_release_channels ON product_versions.product_name 
		= product_release_channels.product_name
		AND product_versions.build_type = product_release_channels.release_channel;

ALTER VIEW product_os_crash_ratio OWNER TO breakpad_rw;
GRANT SELECT ON product_os_crash_ratio TO analyst;