\set ON_ERROR_STOP 1

-- daily update function
CREATE OR REPLACE FUNCTION update_crashes_by_user (
    updateday DATE,
    checkdata BOOLEAN default TRUE,
    check_period INTERVAL default interval '1 hour' )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
SET client_min_messages = 'ERROR'
AS $f$
BEGIN
-- this function populates a daily matview
-- for general statistics of crashes by user
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM crashes_by_user
    WHERE report_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'crashes_by_user has already been run for %.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- check for product_adu

PERFORM 1 FROM product_adu
WHERE adu_date = updateday
LIMIT 1;
IF NOT FOUND THEN
  IF checkdata THEN
    RAISE EXCEPTION 'product_adu has not been updated for %', updateday;
  ELSE
    RETURN FALSE;
  END IF;
END IF;

-- now insert the new records
INSERT INTO crashes_by_user
    ( product_version_id, report_date,
      report_count, adu,
      os_short_name, crash_type_id )
SELECT product_version_id, updateday,
    coalesce(report_count,0), coalesce(adu_sum, 0),
    os_short_name, crash_type_id
FROM ( select product_versions.product_version_id,
            count(reports_clean.uuid) as report_count,
            os_names.os_name, os_short_name, crash_type_id
      FROM product_versions
      	CROSS JOIN crash_types
      	CROSS JOIN os_names
      	LEFT OUTER JOIN reports_clean ON
      		product_versions.product_version_id = reports_clean.product_version_id
      		and utc_day_is(date_processed, updateday)
      		AND reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      		AND reports_clean.os_name = os_names.os_name
      WHERE product_versions.build_date >= ( current_date - interval '2 years' )
      GROUP BY product_versions.product_version_id,
      	os_names.os_name, os_short_name, crash_type_id
      	) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        os_name
        from product_adu
        where adu_date = updateday
        group by product_version_id, os_name ) as sum_adu
      USING ( product_version_id, os_name )
ORDER BY product_version_id;

-- insert records for the rapid beta parent entries
INSERT INTO crashes_by_user
    ( product_version_id, report_date,
      report_count, adu,
      os_short_name, crash_type_id )
SELECT product_versions.rapid_beta_id, updateday,
	sum(report_count), sum(adu),
	os_short_name, crash_type_id
FROM crashes_by_user
	JOIN product_versions USING ( product_version_id )
WHERE rapid_beta_id IS NOT NULL
	AND report_date = updateday
GROUP BY rapid_beta_id, os_short_name, crash_type_id;

RETURN TRUE;
END; $f$;

-- now create a backfill function
-- so that we can backfill missing data
CREATE OR REPLACE FUNCTION backfill_crashes_by_user(
    updateday DATE, check_period INTERVAL DEFAULT INTERVAL '1 hour' )
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$f$
BEGIN

DELETE FROM crashes_by_user WHERE report_date = updateday;
PERFORM update_crashes_by_user(updateday, false, check_period);

RETURN TRUE;
END; $f$;



