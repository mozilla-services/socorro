CREATE OR REPLACE FUNCTION public.update_crashes_by_user_build(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval)
 RETURNS boolean
 LANGUAGE plpgsql
 SET work_mem TO '512MB'
 SET temp_buffers TO '512MB'
 SET client_min_messages TO 'ERROR'
 SET "TimeZone" TO 'UTC'
AS $function$
BEGIN
-- this function populates a daily matview
-- for general statistics of crashes by user
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM crashes_by_user_build
    WHERE report_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'crashes_by_user_build has already been run for %.',updateday;
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

PERFORM 1 FROM build_adu
WHERE adu_date = updateday
LIMIT 1;
IF NOT FOUND THEN
  IF checkdata THEN
    RAISE EXCEPTION 'build_adu has not been updated for %', updateday;
  ELSE
    RETURN FALSE;
  END IF;
END IF;

-- now insert the new records
-- first, nightly and aurora are fairly straightforwards

INSERT INTO crashes_by_user_build
    ( product_version_id, report_date,
      build_date, report_count, adu,
      os_short_name, crash_type_id )
SELECT product_version_id, updateday,
    count_reports.build_date, report_count, adu_sum,
    os_short_name, crash_type_id
FROM ( select product_versions.product_version_id,
            count(DISTINCT reports_clean.uuid) as report_count,
            os_names.os_name, os_short_name, crash_type_id,
            build_date(build_id) as build_date
      FROM product_versions
      	JOIN product_version_builds USING (product_version_id)
      	CROSS JOIN crash_types
      	CROSS JOIN os_names
      	LEFT OUTER JOIN reports_clean ON
      		product_versions.product_version_id = reports_clean.product_version_id
      		and utc_day_is(date_processed, updateday)
      		AND reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      		AND reports_clean.os_name = os_names.os_name
      		AND reports_clean.release_channel IN ('nightly','aurora')
      		AND product_version_builds.build_id = reports_clean.build
      WHERE
          -- only accumulate data for each build for 7 days after build
          updateday <= ( build_date(build_id) + 6 )
      GROUP BY product_versions.product_version_id, os_names.os_name, os_short_name, crash_type_id,
      	build_date(build_id)
    ) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        os_name, build_date
        from build_adu
        where adu_date = updateday
        group by product_version_id, os_name, build_date ) as sum_adu
      USING ( product_version_id, os_name, build_date )
      JOIN product_versions USING ( product_version_id )
ORDER BY product_version_id;

-- rapid beta needs to be inserted with the productid of the
-- parent beta product_version instead of its
-- own product_version_id.

INSERT INTO crashes_by_user_build
    ( product_version_id, report_date,
      build_date, report_count, adu,
      os_short_name, crash_type_id )
SELECT rapid_beta_id, updateday,
    count_reports.build_date, report_count, adu_sum,
    os_short_name, crash_type_id
FROM ( select rapid_beta_id AS product_version_id,
            count(distinct reports_clean.uuid) as report_count,
            os_names.os_name, os_short_name, crash_type_id,
            build_date(build_id) as build_date
      FROM product_versions
        JOIN product_version_builds USING (product_version_id)
      	CROSS JOIN crash_types
      	CROSS JOIN os_names
      	LEFT OUTER JOIN reports_clean ON
      		product_versions.product_version_id = reports_clean.product_version_id
      		and utc_day_is(date_processed, updateday)
      		AND reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      		AND reports_clean.os_name = os_names.os_name
      		AND reports_clean.release_channel = 'beta'
      		AND reports_clean.build = product_version_builds.build_id
      WHERE
          -- only accumulate data for each build for 7 days after build
          updateday <= ( build_date(build_id) + 6 )
          AND product_versions.rapid_beta_id IS NOT NULL
      GROUP BY rapid_beta_id, os_names.os_name, os_short_name, crash_type_id,
      	build_date(build_id)
      	) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        os_name, build_date
        from build_adu
        where adu_date = updateday
        group by product_version_id, os_name, build_date ) as sum_adu
      USING ( product_version_id, os_name, build_date )
      JOIN product_versions USING ( product_version_id )
ORDER BY product_version_id;


RETURN TRUE;
END; $function$

