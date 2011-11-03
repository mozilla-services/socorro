\set ON_ERROR_STOP 1

select create_table_if_not_exists( 'os_signature_counts', $x$
CREATE TABLE os_signature_counts (
	signature_id int not null,
	os_version_string citext not null,
	report_date date not null,
	report_count int not null default 0,
	constraint os_signature_count_key primary key ( signature_id, report_date, os_version_string )
);$x$, 'breakpad_rw', ARRAY [ 'os_version_string', 'report_date' ] );


CREATE OR REPLACE FUNCTION update_os_signature_counts (
	updateday DATE, checkdata BOOLEAN default TRUE )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
AS $f$
BEGIN
-- this function populates a daily matview
-- for os-version and signature counts
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
	PERFORM 1 FROM os_signature_counts
	WHERE report_date = updateday
	LIMIT 1;
	IF FOUND THEN
		RAISE EXCEPTION 'OS-signature counts have already been run for %.',updateday;
	END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday) THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
	ELSE
		RETURN TRUE;
	END IF;
END IF;

INSERT INTO os_signature_counts 
	( signature_id, os_version_string, report_date, report_count )
SELECT signature_id, os_version_string, updateday, count(*) as report_count
FROM reports_clean 
	JOIN product_versions USING (product_version_id)
	JOIN os_versions USING (os_version_id)
WHERE utc_day_is(date_processed, updateday)
	AND tstz_between(date_processed, build_date, sunset_date)
GROUP BY signature_id, os_version_string;

RETURN TRUE;
END; $f$;


CREATE OR REPLACE FUNCTION backfill_os_signature_counts(
	updateday DATE )
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$f$
BEGIN

DELETE FROM os_signature_counts WHERE report_date = updateday;
PERFORM update_os_signature_counts(updateday, false);

RETURN TRUE;
END; $f$;
