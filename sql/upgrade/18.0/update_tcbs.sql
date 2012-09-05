\set ON_ERROR_STOP 1

DROP FUNCTION IF EXISTS update_tcbs(date, boolean);

CREATE OR REPLACE FUNCTION update_tcbs(updateday date,
	checkdata boolean DEFAULT true,
    check_period INTERVAL default interval '1 hour'
	) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages = 'ERROR'
    AS $$
BEGIN
-- this procedure goes throught the daily TCBS update for the
-- new TCBS table
-- designed to be run only once for each day
-- this new version depends on reports_clean

-- check that it hasn't already been run

IF checkdata THEN
	PERFORM 1 FROM tcbs
	WHERE report_date = updateday LIMIT 1;
	IF FOUND THEN
		RAISE NOTICE 'TCBS has already been run for the day %.',updateday;
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

-- populate the matview for regular releases

INSERT INTO tcbs (
	signature_id, report_date, product_version_id,
	process_type, release_channel,
	report_count, win_count, mac_count, lin_count, hang_count,
	startup_count
)
SELECT signature_id, updateday,
	product_version_id,
	process_type, release_channel,
	count(*),
	sum(case when os_name = 'Windows' THEN 1 else 0 END),
	sum(case when os_name = 'Mac OS X' THEN 1 else 0 END),
	sum(case when os_name = 'Linux' THEN 1 else 0 END),
    count(hang_id),
    sum(case when uptime < INTERVAL '1 minute' THEN 1 else 0 END)
FROM reports_clean
	JOIN product_versions USING (product_version_id)
	WHERE utc_day_is(date_processed, updateday)
		AND tstz_between(date_processed, build_date, sunset_date)
GROUP BY signature_id, updateday, product_version_id,
	process_type, release_channel;

-- populate summary statistics for rapid beta parent records

INSERT INTO tcbs (
	signature_id, report_date, product_version_id,
	process_type, release_channel,
	report_count, win_count, mac_count, lin_count, hang_count,
	startup_count )
SELECT signature_id, updateday, rapid_beta_id,
	process_type, release_channel,
	sum(report_count), sum(win_count), sum(mac_count), sum(lin_count),
	sum(hang_count), sum(startup_count)
FROM tcbs
	JOIN product_versions USING (product_version_id)
WHERE report_date = updateday
	AND build_type = 'beta'
	AND rapid_beta_id is not null
GROUP BY signature_id, updateday, rapid_beta_id,
	process_type, release_channel;

-- tcbs_ranking removed until it's being used

-- done
RETURN TRUE;
END;
$$;


