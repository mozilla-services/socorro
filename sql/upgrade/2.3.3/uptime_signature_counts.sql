\set ON_ERROR_STOP 1

select create_table_if_not_exists( 'uptime_levels', $x$
CREATE TABLE uptime_levels (
	uptime_level serial not null primary key,
	uptime_string citext not null unique,
	min_uptime interval not null,
	max_uptime interval not null,
	constraint period_check check ( min_uptime < max_uptime )
);

INSERT INTO uptime_levels ( uptime_string, min_uptime, max_uptime )
VALUES ( '< 1 min', '0 seconds', '1 minute' ),
	( '1-5 min', '1 minute', '5 minutes' ),
	( '5-15 min', '5 minutes', '15 minutes' ),
	( '15-60 min', '15 minutes', '60 minutes' ),
	( '> 1 hour', '60 minutes', 'infinity' );
$x$, 'breakpad_rw' );


select create_table_if_not_exists( 'uptime_signature_counts', $x$
CREATE TABLE uptime_signature_counts (
	uptime_level int not null,
	os_version_id int not null,
	report_date date not null,
	report_count int not null default 0,
	constraint uptime_signature_count_key ( signature_id, report_date, uptime_level )
);$x$, 'breakpad_rw', ARRAY [ 'uptime_level', 'report_date' ] );


CREATE OR REPLACE FUNCTION update_uptime_signature_counts (
	updateday DATE, checkdata BOOLEAN default TRUE )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
AS $f$
BEGIN
-- this function populates a daily matview
-- for uptime buckets and signature counts
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
	PERFORM 1 FROM uptime_signature_counts
	WHERE report_date = updateday
	LIMIT 1;
	IF FOUND THEN
		RAISE EXCEPTION 'Uptime-signature counts have already been run for %.',updateday;
	END IF;
END IF:

-- check if there's any data
PERFORM 1 FROM reports_clean
WHERE utc_day_is(date_processed, updateday) LIMIT 1;
IF NOT FOUND THEN
	IF checkdata THEN
		RAISE EXCEPTION 'No reports_clean data found for %',updateday;
	ELSE
		RETURN TRUE;
	END IF;
END IF;

INSERT INTO uptime_signature_counts 
	( signature_id, uptime_level, report_date, report_count )
SELECT signature_id, uptime_level, updateday, count(*) as report_count
FROM reports_clean
	JOIN uptime_levels ON reports_clean.uptime >= uptime_levels.min_uptime
		AND reports_clean.uptime < uptime_levels.max_uptime
	WHERE utc_day_is(date_processed, updateday)
GROUP BY signature_id, uptime_level;

RETURN TRUE;
END; $f$;


CREATE OR REPLACE FUNCTION backfill_uptime_signature_counts(
	updateday DATE )
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$f$
BEGIN;

DELETE FROM uptime_signature_counts WHERE report_date = updateday;
PERFORM update_uptime_signature_counts(updateday, false);

RETURN TRUE;
END; $f$;
