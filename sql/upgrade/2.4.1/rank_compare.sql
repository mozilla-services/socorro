\set ON_ERROR_STOP 1

-- create new ranking table
-- note that it only holds ranking data for the current date
-- it gets truncated and regenerated every day

SELECT create_table_if_not_exists ( 'rank_compare', $q$
create table rank_compare (
	product_version_id int not null,
	signature_id int not null,
	rank_days int not null,
	report_count int,
	total_reports bigint,
	rank_report_count int,
	percent_of_total numeric,
	constraint rank_compare_key primary key ( product_version_id, signature_id, rank_days )
);$q$, 'breakpad_rw', 
ARRAY [ 'product_version_id,rank_report_count', 'signature_id' ]);

-- update procedure

-- daily update function
CREATE OR REPLACE FUNCTION update_rank_compare (
	updateday DATE default NULL,
	checkdata BOOLEAN default TRUE )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
SET client_min_messages = 'ERROR'
AS $f$
BEGIN
-- this function populates a daily matview
-- for rankings of signatures on TCBS
-- depends on the new reports_clean

-- run for yesterday if not set
updateday := COALESCE(updateday, ( CURRENT_DATE -1 ));

-- don't care if we've been run
-- since there's no historical data

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday) THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
	ELSE
		RETURN TRUE;
	END IF;
END IF;

-- obtain a lock on the matview so that we can TRUNCATE
IF NOT try_lock_table('rank_compare', 'ACCESS EXCLUSIVE') THEN
	RAISE EXCEPTION 'unable to lock the rank_compare table for update.';
END IF;

-- create temporary table with totals from reports_clean

CREATE TEMPORARY TABLE prod_sig_counts 
AS SELECT product_version_id, signature_id, count(*) as report_count
FROM reports_clean
WHERE utc_day_is(date_processed, updateday)
GROUP BY product_version_id, signature_id;

-- truncate rank_compare since we don't need the old data

TRUNCATE rank_compare CASCADE;

-- now insert the new records
INSERT INTO rank_compare (
	product_version_id, signature_id,
	rank_days,
	report_count,
	total_reports, 
	rank_report_count,
	percent_of_total)
SELECT product_version_id, signature_id,
	1, 
	report_count,
	total_count,
	count_rank,
	round(( report_count::numeric / total_count ),5)
FROM (
	SELECT product_version_id, signature_id,
		report_count,
		sum(report_count) over (partition by product_version_id) as total_count,
		dense_rank() over (partition by product_version_id 
							order by report_count desc) as count_rank
	FROM prod_sig_counts
) as initrank;

RETURN TRUE;
END; $f$;

-- now create a backfill function 
-- so that we can backfill missing data
CREATE OR REPLACE FUNCTION backfill_rank_compare(
	updateday DATE DEFAULT NULL)
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$f$
BEGIN

PERFORM update_rank_compare(updateday, false);

RETURN TRUE;
END; $f$;





