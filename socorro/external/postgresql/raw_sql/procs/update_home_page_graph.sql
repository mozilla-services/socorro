CREATE OR REPLACE FUNCTION update_home_page_graph(
    updateday date,
    checkdata boolean DEFAULT true,
    check_period interval DEFAULT '01:00:00'::interval
)
    RETURNS boolean
    LANGUAGE plpgsql
    SET client_min_messages TO 'ERROR'
    SET "TimeZone" TO 'UTC'
AS $$
BEGIN
-- this function populates a daily matview
-- for **new_matview_description**
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM home_page_graph
    WHERE report_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'home_page_graph has already been run for %.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE NOTICE 'Reports_clean has not been updated to the end of %',updateday;
        RETURN FALSE;
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
    RAISE NOTICE 'product_adu has not been updated for %', updateday;
    RETURN FALSE;
  ELSE
    RETURN FALSE;
  END IF;
END IF;

-- now insert the new records
INSERT INTO home_page_graph
    ( product_version_id, report_date,
      report_count, adu, crash_hadu )
SELECT product_version_id, updateday,
    report_count, adu_sum,
    crash_hadu(report_count, adu_sum, throttle)
FROM ( select product_version_id,
            count(*) as report_count
      from reports_clean
        JOIN product_versions USING ( product_version_id )
        JOIN crash_types ON
            reports_clean.process_type = crash_types.process_type
            AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      WHERE
          utc_day_is(date_processed, updateday)
          -- exclude browser hangs from total counts
          AND crash_types.include_agg
          AND updateday BETWEEN build_date AND sunset_date
      group by product_version_id ) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum
        from product_adu
        where adu_date = updateday
        group by product_version_id ) as sum_adu
      USING ( product_version_id )
      JOIN product_versions USING ( product_version_id )
      JOIN product_build_types ON
          product_versions.product_name = product_build_types.product_name
          AND product_versions.build_type_enum::text = product_build_types.build_type::text
WHERE sunset_date > ( current_date - interval '1 year' )
ORDER BY product_version_id;

-- insert summary records for rapid_beta parents
INSERT INTO home_page_graph
    ( product_version_id, report_date,
      report_count, adu, crash_hadu )
SELECT rapid_beta_id, updateday,
    sum(report_count), sum(adu),
    crash_hadu(sum(report_count), sum(adu))
FROM home_page_graph
    JOIN product_versions USING ( product_version_id )
WHERE rapid_beta_id IS NOT NULL
    AND report_date = updateday
GROUP BY rapid_beta_id, updateday;

RETURN TRUE;
END;
$$;
