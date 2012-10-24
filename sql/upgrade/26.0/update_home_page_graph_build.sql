CREATE OR REPLACE FUNCTION public.update_home_page_graph_build(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval)
 RETURNS boolean
 LANGUAGE plpgsql
 SET work_mem TO '512MB'
 SET temp_buffers TO '512MB'
 SET client_min_messages TO 'ERROR'
 SET "TimeZone" TO 'UTC'
AS $function$
BEGIN

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM home_page_graph_build
    WHERE report_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'home_page_graph_build has already been run for %.',updateday;
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

-- now insert the new records for nightly and aurora

INSERT INTO home_page_graph_build
    ( product_version_id, build_date, report_date,
      report_count, adu )
SELECT product_version_id, count_reports.build_date, updateday,
    report_count, adu_sum
FROM ( select product_version_id,
            count(*) as report_count,
            build_date(build) as build_date
      FROM reports_clean
      	JOIN product_versions USING ( product_version_id )
      	JOIN products USING ( product_name )
      	JOIN crash_types ON
      		reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      WHERE
          utc_day_is(date_processed, updateday)
          -- only 7 days of each build
          AND build_date(build) >= ( updateday - 6 )
          -- exclude browser hangs from total counts
          AND crash_types.include_agg
          -- only visible products
          AND updateday BETWEEN product_versions.build_date AND product_versions.sunset_date
          -- aurora, nightly, and rapid beta only
          AND reports_clean.release_channel IN ( 'nightly','aurora' )
      group by product_version_id, build_date(build) ) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        build_date
        from build_adu
        where adu_date = updateday
        group by product_version_id, build_date ) as sum_adu
      USING ( product_version_id, build_date )
      JOIN product_versions USING ( product_version_id )
      JOIN product_release_channels ON
          product_versions.product_name = product_release_channels.product_name
          AND product_versions.build_type = product_release_channels.release_channel
ORDER BY product_version_id;

-- insert records for the "parent" rapid beta

INSERT INTO home_page_graph_build
    ( product_version_id, build_date, report_date,
      report_count, adu )
SELECT product_version_id, count_reports.build_date, updateday,
    report_count, adu_sum
FROM ( select rapid_beta_id AS product_version_id,
            count(*) as report_count,
            build_date(build) as build_date
      FROM reports_clean
      	JOIN product_versions USING ( product_version_id )
      	JOIN products USING ( product_name )
      	JOIN crash_types ON
      		reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      WHERE
          utc_day_is(date_processed, updateday)
          -- only 7 days of each build
          AND build_date(build) >= ( updateday - 6 )
          -- exclude browser hangs from total counts
          AND crash_types.include_agg
          -- only visible products
          AND updateday BETWEEN product_versions.build_date AND product_versions.sunset_date
          -- aurora, nightly, and rapid beta only
          AND reports_clean.release_channel = 'beta'
          AND rapid_beta_id IS NOT NULL
      group by rapid_beta_id, build_date(build) ) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        build_date
        from build_adu
        where adu_date = updateday
        group by product_version_id, build_date ) as sum_adu
      USING ( product_version_id, build_date )
      JOIN product_versions USING ( product_version_id )
      JOIN product_release_channels ON
          product_versions.product_name = product_release_channels.product_name
          AND product_versions.build_type = product_release_channels.release_channel
ORDER BY product_version_id;


RETURN TRUE;
END; $function$

