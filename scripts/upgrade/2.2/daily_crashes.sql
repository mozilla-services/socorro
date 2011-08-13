\set ON_ERROR_STOP 1

BEGIN;

-- we need a code map, dammit
INSERT INTO daily_crash_codes ( crash_code, crash_type )
VALUES ( 'C', 'CRASH_BROWSER' ),
	( 'P', 'OOP_PLUGIN' ),
	( 'H', 'HANGS_NORMALIZED' ),
	( 'c', 'HANG_BROWSER' ),
	( 'p', 'HANG_PLUGIN' ),
	( 'T', 'CONTENT' );
	
-- change the table so that it can hold both old and new crashes
--ALTER TABLE daily_crashes ALTER COLUMN adu_day TYPE date;
ALTER TABLE daily_crashes DROP CONSTRAINT daily_crashes_productdims_id_fkey;

-- code-mapping function
CREATE OR REPLACE FUNCTION daily_crash_code (
	process_type text, hangid text )
RETURNS char(1)
LANGUAGE SQL 
IMMUTABLE AS $f$
SELECT CASE
	WHEN $1 ILIKE 'content' THEN 'T'
	WHEN $1 IS NULL AND $2 IS NULL THEN 'C'
	WHEN $1 IS NULL AND $2 IS NOT NULL THEN 'c'
	WHEN $1 ILIKE 'plugin' AND $2 IS NULL THEN 'P'
	WHEN $1 ILIKE 'plugin' AND $2 IS NOT NULL THEN 'p'
	ELSE 'C'
	END
$f$;

COMMIT;

-- new daily_crashes update job.  replaces daily_crashes.py

CREATE OR REPLACE FUNCTION update_daily_crashes (
	updateday date )
RETURNS BOOLEAN
LANGUAGE plpgsql 
SET work_mem = '512MB'
SET temp_buffers = '512MB'
AS $f$
BEGIN
-- update the old daily crashes  yes, this is horrible
-- stuff, but until we overhaul the home page graph
-- we will continue to use it

-- apologies for badly written SQL, didn't want to rewrite it all from scratch

-- note: we are currently excluding crashes which are missing an OS_Name from the count

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
JOIN reports on product_versions.product_name = reports.product 
	AND product_versions.version_string = reports.version
WHERE 
	date_processed >= utc_day_begins_pacific(updateday)
		AND date_processed < utc_day_ends_pacific(updateday)
    AND ( lower(release_channel) NOT IN ( 'nightly', 'beta', 'aurora' )
        OR release_channel IS NULL )
	AND updateday BETWEEN product_versions.build_date and sunset_date
    AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac') 
AND product_versions.build_type <> 'beta'
GROUP BY product_version_id, crash_code, os_short_name;

-- insert crash counts for new products
-- betas
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT COUNT(*) as count, daily_crash_code(process_type, hangid) as crash_code, 
	product_versions.product_version_id,
	substring(os_name, 1, 3) AS os_short_name,
	updateday
FROM product_versions
JOIN product_version_builds USING (product_version_id)
JOIN reports on product_versions.product_name = reports.product 
	AND product_versions.release_version = reports.version
	AND product_version_builds.build_id = build_numeric(reports.build)
WHERE date_processed >= utc_day_begins_pacific(updateday)
		AND date_processed < utc_day_ends_pacific(updateday)
    AND release_channel ILIKE 'beta'
	AND updateday BETWEEN product_versions.build_date and sunset_date
    AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac') 
AND product_versions.build_type = 'beta'
GROUP BY product_version_id, crash_code, os_short_name;

-- insert normalized hangs for new products
-- non-beta
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT count(subr.hangid) as count, 'H', subr.prod_id, subr.os_short_name,
	 updateday
FROM (
		   SELECT distinct hangid, product_version_id AS prod_id, substring(os_name, 1, 3) AS os_short_name
			FROM product_versions
			JOIN reports on product_versions.product_name = reports.product 
				AND product_versions.version_string = reports.version
			WHERE date_processed >= utc_day_begins_pacific(updateday)
					AND date_processed < utc_day_ends_pacific(updateday)
                AND ( lower(release_channel) NOT IN ( 'nightly', 'beta', 'aurora' )
                      or release_channel is null )
				AND updateday BETWEEN product_versions.build_date and sunset_date
			AND product_versions.build_type <> 'beta'
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
			JOIN product_version_builds USING (product_version_id)
			JOIN reports on product_versions.product_name = reports.product 
				AND product_versions.release_version = reports.version
				AND product_version_builds.build_id = build_numeric(reports.build)
			WHERE date_processed >= utc_day_begins_pacific(updateday)
					AND date_processed < utc_day_ends_pacific(updateday)
                AND release_channel ILIKE 'beta'
				AND updateday BETWEEN product_versions.build_date and sunset_date
			AND product_versions.build_type = 'beta'
            AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac') 
		 ) AS subr
GROUP BY subr.prod_id, subr.os_short_name;

ANALYZE daily_crashes;

RETURN TRUE;

END;$f$;


DO $f$
DECLARE tcdate DATE;
	enddate DATE;
BEGIN

tcdate := '2011-04-17';
enddate := '2011-08-09';
-- timelimited version for stage/dev
--tcdate := '2011-07-25';
--enddate := '2011-08-09';

WHILE tcdate < enddate LOOP

	DELETE FROM daily_crashes WHERE adu_day = tcdate;
	PERFORM update_daily_crashes(tcdate);
	RAISE INFO 'daily crashes updated for %',tcdate;
	tcdate := tcdate + 1;
	
END LOOP;
END; $f$;


