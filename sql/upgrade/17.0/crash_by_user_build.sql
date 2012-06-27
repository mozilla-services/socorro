\set ON_ERROR_STOP 1

-- create new table for crashes_by_user and build

SELECT create_table_if_not_exists('crashes_by_user_build',
$t$
CREATE TABLE crashes_by_user_build (
 product_version_id int not null,
 os_short_name citext not null,
 crash_type_id int not null references crash_types(crash_type_id),
 build_date date not null,
 report_date date not null,
 report_count int not null,
 adu int not null,
 CONSTRAINT crashes_by_user_build_key PRIMARY KEY ( product_version_id, build_date, report_date, os_short_name, crash_type_id )
);$t$, 'breakpad_rw' );

CREATE OR REPLACE VIEW crashes_by_user_build_view AS
SELECT crashes_by_user_build.product_version_id,
  product_versions.product_name, version_string,
  os_short_name, os_name, crash_type, crash_type_short,
  crashes_by_user_build.build_date,
  sum(report_count) as report_count,
  sum(report_count / throttle) as adjusted_report_count,
  sum(adu) as adu, throttle
FROM crashes_by_user_build
  JOIN product_versions USING (product_version_id)
  JOIN product_release_channels ON
    product_versions.product_name = product_release_channels.product_name
    AND product_versions.build_type = product_release_channels.release_channel
  JOIN os_names USING (os_short_name)
  JOIN crash_types USING (crash_type_id)
GROUP BY crashes_by_user_build.product_version_id,
  product_versions.product_name, version_string,
  os_short_name, os_name, crash_type, crash_type_short,
  crashes_by_user_build.build_date, throttle;

-- daily update function
CREATE OR REPLACE FUNCTION update_crashes_by_user_build (
    updateday DATE,
    checkdata BOOLEAN default TRUE,
    check_period INTERVAL default interval '1 hour' )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
SET client_min_messages = 'ERROR'
SET timezone = 'UTC'
AS $f$
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
FROM ( select product_version_id,
            count(*) as report_count,
            os_name, os_short_name, crash_type_id,
            build_date(build) as build_date
      from reports_clean
      	JOIN product_versions USING ( product_version_id )
      	JOIN products USING ( product_name )
      	JOIN crash_types ON
      		reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      	JOIN os_names USING ( os_name )
      WHERE
          utc_day_is(date_processed, updateday)
          -- only accumulate data for each build for 7 days after build
          AND updateday <= ( build_date(build) + 6 )
          AND reports_clean.release_channel IN ( 'nightly','aurora' )
      GROUP BY product_version_id, os_name, os_short_name, crash_type_id,
      	build_date(build)
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
            count(*) as report_count,
            os_name, os_short_name, crash_type_id,
            build_date(build) as build_date
      from reports_clean
      	JOIN product_versions USING ( product_version_id )
      	JOIN products USING ( product_name )
      	JOIN crash_types ON
      		reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      	JOIN os_names USING ( os_name )
      WHERE
          utc_day_is(date_processed, updateday)
          -- only accumulate data for each build for 7 days after build
          AND updateday <= ( build_date(build) + 6 )
          AND reports_clean.release_channel = 'beta'
          AND product_versions.rapid_beta_id IS NOT NULL
      GROUP BY product_version_id, os_name, os_short_name, crash_type_id,
      	build_date(build)
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
END; $f$;

-- now create a backfill function
-- so that we can backfill missing data
CREATE OR REPLACE FUNCTION backfill_crashes_by_user_build(
    updateday DATE, check_period INTERVAL DEFAULT INTERVAL '1 hour' )
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$f$
BEGIN

DELETE FROM crashes_by_user_build WHERE report_date = updateday;
PERFORM update_crashes_by_user_build(updateday, false, check_period);

RETURN TRUE;
END; $f$;


-- sample backfill script
-- for initialization
DO $f$
DECLARE
    thisday DATE := ( current_date - 7 );
    lastday DATE;
BEGIN

    -- set backfill to the last day we have ADU for
    SELECT max("date")
    INTO lastday
    FROM product_adu;

    WHILE thisday <= lastday LOOP

        RAISE INFO 'backfilling %', thisday;

        PERFORM backfill_crashes_by_user_build(thisday);

        thisday := thisday + 1;

    END LOOP;

END;$f$;
