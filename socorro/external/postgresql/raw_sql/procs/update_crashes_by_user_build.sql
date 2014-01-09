CREATE OR REPLACE FUNCTION update_crashes_by_user_build(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET client_min_messages TO 'ERROR'
    SET "TimeZone" TO 'UTC'
    AS $$
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
        RAISE NOTICE 'Reports_clean has not been updated to the end of %',updateday;
        RETURN FALSE;
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
    RAISE NOTICE 'build_adu has not been updated for %', updateday;
    RETURN FALSE;
  ELSE
    RETURN FALSE;
  END IF;
END IF;

-- now insert the new records
-- first, nightly and aurora are fairly straightforward

INSERT INTO crashes_by_user_build (
    product_version_id
    , report_date
    , build_date
    , report_count
    , adu
    , os_short_name
    , crash_type_id
)
WITH count_reports AS (
    select
        product_versions.product_version_id
        , count(DISTINCT reports_clean.uuid) as report_count
        , os_names.os_name
        , os_short_name
        , crash_type_id
        , build_date(build_id) as build_date
    FROM product_versions
        JOIN product_version_builds USING (product_version_id)
        CROSS JOIN crash_types
        CROSS JOIN os_names
        LEFT OUTER JOIN reports_clean ON
            product_versions.product_version_id = reports_clean.product_version_id
        AND utc_day_is(date_processed, updateday)
        AND reports_clean.process_type = crash_types.process_type
        AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
        AND reports_clean.os_name = os_names.os_name
        AND reports_clean.release_channel IN ('nightly','aurora')
        AND product_version_builds.build_id = reports_clean.build
    GROUP BY
        product_versions.product_version_id
        , os_names.os_name
        , os_short_name
        , crash_type_id
        , build_date(build_id)
),
sum_adu AS (
    select
        product_version_id
        , sum(adu_count) as adu_sum
        , os_name
        , build_date
    FROM build_adu
    WHERE adu_date = updateday
    group by
        product_version_id
        , os_name
        , build_date
)
SELECT
    product_version_id
    , updateday
    , count_reports.build_date
    , report_count
    , adu_sum
    , os_short_name
    , crash_type_id
FROM
    count_reports
    JOIN sum_adu USING ( product_version_id, os_name, build_date )
    JOIN product_versions USING ( product_version_id )
ORDER BY product_version_id;

-- The following query only inserts counts for product_versions with
-- is_rapid_beta == True and for beta versions which are 7 days old or newer,
-- and have their rapid_beta_id set.

INSERT INTO crashes_by_user_build (
    product_version_id
    , report_date
    , build_date
    , report_count
    , adu
    , os_short_name
    , crash_type_id
)
WITH count_reports AS (
    select
        rapid_beta_id AS product_version_id
        -- This is a confusing alias that allows us to utilize USING
        -- in a later query. Possibly ill-advised renaming.
        , count(distinct reports_clean.uuid) as report_count
        , os_names.os_name
        -- Including the os_name because build_adu uses this instead of
        -- the short name. Might want to change this to just os_short_name.
        , os_short_name
        , crash_type_id
        , build_date(build_id) as build_date
    FROM product_versions
        JOIN product_version_builds USING (product_version_id)
        CROSS JOIN crash_types
        CROSS JOIN os_names
        -- These cross joins produce all the possible combinations of
        -- crash types and os_names, resulting in some counts being zero
        -- if we didn't see any crashes for those combos on a given day.
        -- Which explains the left outer join below -- which allows us
        -- to have zero crashes for certain combos.
        LEFT OUTER JOIN reports_clean ON
            product_versions.product_version_id = reports_clean.product_version_id
            and utc_day_is(date_processed, updateday)
            AND reports_clean.process_type = crash_types.process_type
            AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
            AND reports_clean.os_name = os_names.os_name
            AND reports_clean.release_channel = 'beta'
            AND reports_clean.build = product_version_builds.build_id
      WHERE
            -- Query is exclusive to betas which have been associated
            -- with a product_version with is_rapid_beta == True
            rapid_beta_id IS NOT NULL
      GROUP BY
        rapid_beta_id
        , os_names.os_name
        , os_short_name
        , crash_type_id
        , build_date(build_id)
),
sum_adu AS (
    select
        product_version_id
        , sum(adu_count) as adu_sum
        , os_name
        , build_adu.build_date
    FROM build_adu
        JOIN product_versions USING (product_version_id)
    WHERE
        adu_date = updateday
        and is_rapid_beta
        -- We're only concerned about rapid_beta releases.
        -- update_build_adu calculates aggregates of the last
        -- 7 days of betas for a particular group of releases
    GROUP BY
        product_version_id
        , os_name
        , build_adu.build_date
        -- We don't need a group by for crash type because
        -- ADU is global, unrelated to kind of crash
)
SELECT
    product_version_id
    , updateday
    , count_reports.build_date
    , report_count
    , adu_sum
    , os_short_name
    , crash_type_id
FROM
    count_reports
    JOIN sum_adu USING ( product_version_id, os_name, build_date )
ORDER BY product_version_id;

RETURN TRUE;
END; $$;
