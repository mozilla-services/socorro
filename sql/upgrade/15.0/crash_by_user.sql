\set ON_ERROR_STOP 1

-- create and populate new table for crash_types
-- note: this assumes that content crashes never hang.  to date that's been 100% true
-- but could lead to breakage in the future.

SELECT create_table_if_not_exists('crash_types',
$t$
CREATE TABLE crash_types (
	crash_type_id SERIAL NOT NULL PRIMARY KEY,
	crash_type CITEXT NOT NULL,
	crash_type_short CITEXT NOT NULL,
	process_type CITEXT NOT NULL references process_types(process_type),
	has_hang_id BOOLEAN,
	CONSTRAINT crash_type_key UNIQUE (crash_type),
	CONSTRAINT crash_type_short_key UNIQUE (crash_type_short)
);

INSERT INTO crash_types ( crash_type, crash_type_short,
	process_type, has_hang_id )
VALUES ( 'Browser', 'crash', 'browser', false ),
	( 'OOP Plugin', 'oop', 'plugin', false ),
	( 'Hang Browser', 'hang-b', 'plugin', true ),
	( 'Hang Plugin', 'hang-p', 'browser', true ),
	( 'Content', 'content', 'content', false );
$t$, 'breakpad_rw');

-- create new table for home page graph

SELECT create_table_if_not_exists('crashes_by_user',
$t$
CREATE TABLE crashes_by_user (
 product_version_id int not null,
 os_short_name citext not null,
 crash_type_id int not null references crash_types(crash_type_id),
 report_date date not null,
 report_count int not null,
 adu int not null,
 CONSTRAINT crashes_by_user_key PRIMARY KEY ( product_version_id, report_date, os_short_name, crash_type_id )
);$t$, 'breakpad_rw' );

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
SET timezone = 'UTC'
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
    report_count, adu_sum,
    os_short_name, crash_type_id
FROM ( select product_version_id,
            count(*) as report_count,
            os_name, os_short_name, crash_type_id
      from reports_clean
      	JOIN product_versions USING ( product_version_id )
      	JOIN crash_types ON
      		reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      	JOIN os_names USING ( os_name )
      WHERE
          utc_day_is(date_processed, updateday)
          -- only keep accumulating data for a year
          AND build_date >= ( current_date - interval '1 year' )
      GROUP BY product_version_id, os_name, os_short_name, crash_type_id
      	) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        os_name
        from product_adu
        where adu_date = updateday
        group by product_version_id, os_name ) as sum_adu
      USING ( product_version_id, os_name )
      JOIN product_versions USING ( product_version_id )
ORDER BY product_version_id;

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

        PERFORM backfill_crashes_by_user(thisday);

        thisday := thisday + 1;

    END LOOP;

END;$f$;
