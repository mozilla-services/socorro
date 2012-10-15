\set ON_ERROR_STOP 1

BEGIN;

CREATE OR REPLACE FUNCTION public.update_nightly_builds(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval)
 RETURNS boolean
 LANGUAGE plpgsql
 SET work_mem TO '512MB'
 SET temp_buffers TO '512MB'
 SET client_min_messages TO 'ERROR'
AS $function$
BEGIN
-- this function populates a daily matview
-- for **new_matview_description**
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
	PERFORM 1 FROM nightly_builds
	WHERE report_date = updateday
	LIMIT 1;
	IF FOUND THEN
		RAISE EXCEPTION 'nightly_builds has already been run for %.',updateday;
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

-- now insert the new records
-- this should be some appropriate query, this simple group by
-- is just provided as an example
INSERT INTO nightly_builds (
	product_version_id, build_date, report_date,
	days_out, report_count )
SELECT product_version_id,
	build_date(reports_clean.build) as build_date,
	date_processed::date as report_date,
	date_processed::date
		- build_date(reports_clean.build) as days_out,
	count(*)
FROM reports_clean
	join product_versions using (product_version_id)
	join product_version_builds using (product_version_id)
WHERE
	reports_clean.build = product_version_builds.build_id
	and reports_clean.release_channel IN ( 'nightly', 'aurora' )
	and date_processed::date
		- build_date(reports_clean.build) <= 14
	and tstz_between(date_processed, build_date, sunset_date)
	and utc_day_is(date_processed,updateday)
GROUP BY product_version_id, product_name, version_string,
	build_date(build), date_processed::date
ORDER BY product_version_id, build_date, days_out;

RETURN TRUE;
END; $function$
;

drop function update_nightly_builds(date, boolean);
COMMIT;
