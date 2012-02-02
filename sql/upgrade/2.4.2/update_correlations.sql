\set ON_ERROR_STOP 1

-- daily update function
CREATE OR REPLACE FUNCTION update_correlations (
	updateday DATE, checkdata BOOLEAN default TRUE )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
SET client_min_messages = 'ERROR'
AS $f$
BEGIN
-- this function populates daily matviews
-- for some of the correlation reports
-- depends on reports_clean

-- no need to check if we've been run, since the correlations
-- only hold the last day of data

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday) THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
	ELSE
		RETURN TRUE;
	END IF;
END IF;

-- clear the correlations list
-- can't use TRUNCATE here because of locking
DELETE FROM correlations;

--create the correlations list
INSERT INTO correlations ( signature_id, product_version_id
	os_name, reason_id, crash_count )
SELECT signature_id, product_version_id,
	os_name, reason_id, count(*)
FROM reports_clean
	JOIN product_versions USING ( product_version_id )
WHERE updateday BETWEEN release_date and sunset_date
	and utc_day_is(date_processed, updateday)
GROUP BY product_version_id, os_name, reason_id, signature_id
ORDER BY product_version_id, os_name, reason_id, signature_id;

ANALYZE correlations;

--create the correlation-addons list
INSERT INTO correlations_addons (
	correlation_id, addon_key, addon_version, count(*) )
SELECT correlation_id, addon_key, addon_version, count(*)
FROM correlations 
	JOIN reports_clean 
		USING ( product_version_id, os_name, reason_id, signature_id )
	JOIN extensions 
		USING ( uuid )
	JOIN product_versions 
		USING ( product_version_id )
WHERE utc_day_is(reports_clean.date_processed, updateday)
	AND utc_day_is(extensions.date_processed, updateday)
	AND updateday BETWEEN release_date AND sunset_date
GROUP BY correlation_id, addon_key, addon_version;

ANALYZE correlations_addons;

--create correlations-cores list
INSERT INTO correlations_cores (
	correlation_id, architecture, cores, count(*) )
SELECT correlation_id, architecture, cores, count(*)
FROM correlations 
	JOIN reports_clean 
		USING ( product_version_id, os_name, reason_id, signature_id )
	JOIN product_versions 
		USING ( product_version_id )
WHERE utc_day_is(reports_clean.date_processed, updateday)
	AND updateday BETWEEN release_date AND sunset_date
GROUP BY correlation_id, architecture, cores;

ANALYZE correlations_cores;

RETURN TRUE;
END; $f$;

-- now create a backfill function 
-- so that we can backfill missing data
CREATE OR REPLACE FUNCTION backfill_correlations(
	updateday DATE )
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$f$
BEGIN

PERFORM update_correlations(updateday, false);

RETURN TRUE;
END; $f$;