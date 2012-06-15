\set ON_ERROR_STOP 1

CREATE OR REPLACE FUNCTION backfill_daily_crashes (
	updateday date, forproduct text default '' )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
AS $f$
DECLARE myproduct CITEXT := forproduct::citext;
BEGIN
-- deletes and replaces daily_crashes for selected dates and optional products
-- intended to be called administratively by backfill_matviews

-- note: we are currently excluding crashes which are missing an OS_Name from the count

-- delete daily_crashes rows

DELETE FROM daily_crashes
USING product_versions
WHERE adu_day = updateday
  AND productdims_id = product_version_id
  AND ( product_name = myproduct or myproduct = '' );

DELETE FROM daily_crashes
USING productdims
WHERE adu_day = updateday
  AND daily_crashes.productdims_id = productdims.id
  AND ( product = myproduct or myproduct = '' );

-- insert old browser crashes
-- for most crashes
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT COUNT(*) as count, daily_crash_code(process_type, hangid) as crash_code, p.id,
	substring(r.os_name, 1, 3) AS os_short_name,
	updateday
FROM product_visibility cfg
JOIN productdims p on cfg.productdims_id = p.id
JOIN reports r on p.product = r.product AND p.version = r.version
WHERE NOT cfg.ignore AND
	date_processed >= utc_day_begins_pacific(updateday)
		AND date_processed < utc_day_ends_pacific(updateday)
	AND updateday BETWEEN cfg.start_date and cfg.end_date
    AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
    AND ( p.product = myproduct or myproduct = '' )
GROUP BY p.id, crash_code, os_short_name;

 -- insert HANGS_NORMALIZED from old data
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT count(subr.hangid) as count, 'H', subr.prod_id, subr.os_short_name,
	 updateday
FROM (
		   SELECT distinct hangid, p.id AS prod_id, substring(r.os_name, 1, 3) AS os_short_name
		   FROM product_visibility cfg
		   JOIN productdims p on cfg.productdims_id = p.id
		   JOIN reports r on p.product = r.product AND p.version = r.version
		   WHERE NOT cfg.ignore AND
				date_processed >= utc_day_begins_pacific(updateday)
					AND date_processed < utc_day_ends_pacific(updateday)
				AND updateday BETWEEN cfg.start_date and cfg.end_date
				AND hangid IS NOT NULL
                AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
                AND ( p.product = myproduct or myproduct = '' )
		 ) AS subr
GROUP BY subr.prod_id, subr.os_short_name;

-- insert crash counts for new products
-- non-beta
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT COUNT(*) as count, daily_crash_code(process_type, hangid) as crash_code,
	product_versions.product_version_id,
	substring(os_name, 1, 3) AS os_short_name,
	updateday
FROM product_versions
JOIN reports on product_versions.product_name = reports.product::citext
	AND product_versions.version_string = reports.version::citext
WHERE
	date_processed >= utc_day_begins_pacific(updateday)
		AND date_processed < utc_day_ends_pacific(updateday)
    AND ( lower(release_channel) NOT IN ( 'nightly', 'beta', 'aurora' )
        OR release_channel IS NULL )
	AND updateday BETWEEN product_versions.build_date and sunset_date
    AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
    AND product_versions.build_type <> 'beta'
    AND ( product_name = myproduct or myproduct = '' )
GROUP BY product_version_id, crash_code, os_short_name;

-- insert crash counts for new products
-- betas
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT COUNT(*) as count, daily_crash_code(process_type, hangid) as crash_code,
	product_versions.product_version_id,
	substring(os_name, 1, 3) AS os_short_name,
	updateday
FROM product_versions
JOIN reports on product_versions.product_name = reports.product::citext
	AND product_versions.release_version = reports.version::citext
WHERE date_processed >= utc_day_begins_pacific(updateday)
		AND date_processed < utc_day_ends_pacific(updateday)
    AND release_channel ILIKE 'beta'
	AND updateday BETWEEN product_versions.build_date and sunset_date
    AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
    AND EXISTS (SELECT 1
        FROM product_version_builds
        WHERE product_versions.product_version_id = product_version_builds.product_version_id
          AND product_version_builds.build_id = build_numeric(reports.build) )
    AND product_versions.build_type = 'beta'
    AND ( product_name = myproduct or myproduct = '' )
GROUP BY product_version_id, crash_code, os_short_name;

-- insert normalized hangs for new products
-- non-beta
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT count(subr.hangid) as count, 'H', subr.prod_id, subr.os_short_name,
	 updateday
FROM (
		   SELECT distinct hangid, product_version_id AS prod_id, substring(os_name, 1, 3) AS os_short_name
			FROM product_versions
			JOIN reports on product_versions.product_name = reports.product::citext
				AND product_versions.version_string = reports.version::citext
			WHERE date_processed >= utc_day_begins_pacific(updateday)
					AND date_processed < utc_day_ends_pacific(updateday)
                AND ( lower(release_channel) NOT IN ( 'nightly', 'beta', 'aurora' )
                      or release_channel is null )
				AND updateday BETWEEN product_versions.build_date and sunset_date
			AND product_versions.build_type <> 'beta'
            AND ( product_name = myproduct or myproduct = '' )
            AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
		 ) AS subr
GROUP BY subr.prod_id, subr.os_short_name;

-- insert normalized hangs for new products
-- beta
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT count(subr.hangid) as count, 'H', subr.prod_id, subr.os_short_name,
	 updateday
FROM (
		   SELECT distinct hangid, product_version_id AS prod_id, substring(os_name, 1, 3) AS os_short_name
			FROM product_versions
			JOIN reports on product_versions.product_name = reports.product::citext
				AND product_versions.release_version = reports.version::citext
			WHERE date_processed >= utc_day_begins_pacific(updateday)
					AND date_processed < utc_day_ends_pacific(updateday)
                AND release_channel ILIKE 'beta'
				AND updateday BETWEEN product_versions.build_date and sunset_date
                AND EXISTS (SELECT 1
                    FROM product_version_builds
                    WHERE product_versions.product_version_id = product_version_builds.product_version_id
                      AND product_version_builds.build_id = build_numeric(reports.build) )
			AND product_versions.build_type = 'beta'
            AND ( product_name = myproduct or myproduct = '' )
            AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
		 ) AS subr
GROUP BY subr.prod_id, subr.os_short_name;

RETURN TRUE;

END;$f$;

