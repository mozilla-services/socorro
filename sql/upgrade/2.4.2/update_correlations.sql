/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
INSERT INTO correlations ( signature_id, product_version_id,
	os_name, reason_id, crash_count )
SELECT signature_id, product_version_id,
	os_name, reason_id, count(*)
FROM reports_clean
	JOIN product_versions USING ( product_version_id )
WHERE updateday BETWEEN build_date and sunset_date
	and utc_day_is(date_processed, updateday)
GROUP BY product_version_id, os_name, reason_id, signature_id
ORDER BY product_version_id, os_name, reason_id, signature_id;

ANALYZE correlations;

-- create list of UUID-report_id correspondences for the day
CREATE TEMPORARY TABLE uuid_repid
AS
SELECT uuid, id as report_id
FROM reports
WHERE utc_day_is(date_processed, updateday)
ORDER BY uuid, report_id;
CREATE INDEX uuid_repid_key on uuid_repid(uuid, report_id);
ANALYZE uuid_repid;

--create the correlation-addons list
INSERT INTO correlation_addons (
	correlation_id, addon_key, addon_version, crash_count )
SELECT correlation_id, extension_id, extension_version, count(*)
FROM correlations 
	JOIN reports_clean 
		USING ( product_version_id, os_name, reason_id, signature_id )
	JOIN uuid_repid 
		USING ( uuid )
	JOIN extensions 
		USING ( report_id )
	JOIN product_versions 
		USING ( product_version_id )
WHERE utc_day_is(reports_clean.date_processed, updateday)
	AND utc_day_is(extensions.date_processed, updateday)
	AND updateday BETWEEN build_date AND sunset_date
GROUP BY correlation_id, extension_id, extension_version;

ANALYZE correlation_addons;

--create correlations-cores list
INSERT INTO correlation_cores (
	correlation_id, architecture, cores, crash_count )
SELECT correlation_id, architecture, cores, count(*)
FROM correlations 
	JOIN reports_clean 
		USING ( product_version_id, os_name, reason_id, signature_id )
	JOIN product_versions 
		USING ( product_version_id )
WHERE utc_day_is(reports_clean.date_processed, updateday)
	AND updateday BETWEEN build_date AND sunset_date
	AND architecture <> '' AND cores >= 0
GROUP BY correlation_id, architecture, cores;

ANALYZE correlation_cores;

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