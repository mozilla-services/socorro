\set ON_ERROR_STOP 1

select create_table_if_not_exists( 'product_signature_counts', $x$
CREATE TABLE product_signature_counts (
	signature_id int not null,
	product_version_id int not null,
	report_date date not null,
	report_count int not null default 0,
	constraint product_signature_count_key ( signature_id, report_date, product_version_id )
);$x$, 'breakpad_rw', ARRAY [ 'product_version_id', 'report_date' ] );


CREATE OR REPLACE FUNCTION update_product_signature_counts (
	updateday DATE, checkdata BOOLEAN default TRUE )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
AS $f$
BEGIN
-- this function populates a daily matview
-- for product-version and signature counts
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
	PERFORM 1 FROM product_signature_counts
	WHERE report_date = updateday
	LIMIT 1;
	IF FOUND THEN
		RAISE EXCEPTION 'product-signature counts have already been run for %.',updateday;
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

INSERT INTO product_signature_counts 
	( signature_id, product_version_id, report_date, report_count )
SELECT signature_id, product_version_id, updateday, count(*) as report_count
FROM reports_clean
	WHERE utc_day_is(date_processed, updateday)
GROUP BY signature_id, os_version_id;

RETURN TRUE;
END; $f$;


CREATE OR REPLACE FUNCTION backfill_product_signature_counts(
	updateday DATE )
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$f$
BEGIN;

DELETE FROM product_signature_counts WHERE report_date = updateday;
PERFORM update_product_signature_counts(updateday, false);

RETURN TRUE;
END; $f$;