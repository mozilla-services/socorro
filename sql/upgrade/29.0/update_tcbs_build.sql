\set ON_ERROR_STOP 1

BEGIN;

CREATE OR REPLACE FUNCTION public.update_tcbs_build(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval)
 RETURNS boolean
 LANGUAGE plpgsql
 SET client_min_messages TO 'ERROR'
AS $function$
BEGIN
-- this procedure goes throught the daily TCBS update for the
-- new TCBS table
-- designed to be run only once for each day
-- this new version depends on reports_clean

-- check that it hasn't already been run

IF checkdata THEN
	PERFORM 1 FROM tcbs_build
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
		RAISE INFO 'reports_clean not updated';
		RETURN FALSE;
	END IF;
END IF;

-- populate the matview for nightly and aurora

INSERT INTO tcbs_build (
	signature_id, build_date,
	report_date, product_version_id,
	process_type, release_channel,
	report_count, win_count, mac_count, lin_count, hang_count,
	startup_count
)
SELECT signature_id, build_date(build),
	updateday, product_version_id,
	process_type, release_channel,
	count(*),
	sum(case when os_name = 'Windows' THEN 1 else 0 END),
	sum(case when os_name = 'Mac OS X' THEN 1 else 0 END),
	sum(case when os_name = 'Linux' THEN 1 else 0 END),
    count(hang_id),
    sum(case when uptime < INTERVAL '1 minute' THEN 1 else 0 END)
FROM reports_clean
	JOIN product_versions USING (product_version_id)
	JOIN products USING ( product_name )
WHERE utc_day_is(date_processed, updateday)
		AND tstz_between(date_processed, build_date, sunset_date)
	-- 7 days of builds only
	AND updateday <= ( build_date(build) + 6 )
	-- only nightly, aurora, and rapid beta
	AND reports_clean.release_channel IN ( 'nightly','aurora' )
	AND version_matches_channel(version_string, release_channel)
GROUP BY signature_id, build_date(build), product_version_id,
	process_type, release_channel;

-- populate for rapid beta parent records only

INSERT INTO tcbs_build (
	signature_id, build_date,
	report_date, product_version_id,
	process_type, release_channel,
	report_count, win_count, mac_count, lin_count, hang_count,
	startup_count
)
SELECT signature_id, build_date(build),
	updateday, rapid_beta_id,
	process_type, release_channel,
	count(*),
	sum(case when os_name = 'Windows' THEN 1 else 0 END),
	sum(case when os_name = 'Mac OS X' THEN 1 else 0 END),
	sum(case when os_name = 'Linux' THEN 1 else 0 END),
    count(hang_id),
    sum(case when uptime < INTERVAL '1 minute' THEN 1 else 0 END)
FROM reports_clean
	JOIN product_versions USING (product_version_id)
	JOIN products USING ( product_name )
WHERE utc_day_is(date_processed, updateday)
		AND tstz_between(date_processed, build_date, sunset_date)
	-- 7 days of builds only
	AND updateday <= ( build_date(build) + 6 )
	-- only nightly, aurora, and rapid beta
	AND reports_clean.release_channel = 'beta'
	AND rapid_beta_id is not null
GROUP BY signature_id, build_date(build), rapid_beta_id,
	process_type, release_channel;

-- tcbs_ranking removed until it's being used

-- done
RETURN TRUE;
END;
$function$

;

COMMIT;
