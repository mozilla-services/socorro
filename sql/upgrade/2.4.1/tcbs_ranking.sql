\set ON_ERROR_STOP 1

-- create new ranking table
-- note that we added this in 2.2 and then dropped it because it
-- wasn't being used.

SELECT create_table_if_not_exists ( 'tcbs_ranking', $q$
create table tcbs_ranking (
	product_version_id int not null,
	signature_id int not null,
	report_date DATE not null,
	process_type citext,
	total_reports bigint,
	rank_report_count int,
	percent_of_total numeric,
	constraint tcbs_ranking_key primary key ( product_version_id, signature_id, process_type, report_date )
);$q$, 'breakpad_rw', 
ARRAY [ 'product_version_id', 'signature_id', 'report_date' ]);

-- update procedure

-- daily update function
CREATE OR REPLACE FUNCTION update_tcbs_ranking (
	updateday DATE, checkdata BOOLEAN default TRUE )
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

-- check if we've been run
IF checkdata THEN
	PERFORM 1 FROM tcbs_ranking
	WHERE report_date = updateday
	LIMIT 1;
	IF FOUND THEN
		RAISE EXCEPTION 'tcbs_ranking has already been run for %.',updateday;
	END IF;
END IF;

-- check if tcbs is complete
PERFORM 1 FROM tcbs
WHERE report_date = updateday
LIMIT 1;
IF NOT FOUND THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
	ELSE
		RETURN TRUE;
	END IF;
END IF;

-- now insert the new records
INSERT INTO tcbs_ranking (
	product_version_id, signature_id,
	process_type, 
	total_reports, rank_report_count )
SELECT product_version_id, signature_id,
	'All', 
	sum(report_count) over () as total_count,
	dense_rank() over (order by report_count desc) as tcbs_rank
FROM (
	SELECT product_version_id, signature_id,
	sum(report_count) as report_count
	FROM tcbs
	WHERE report_date = updateday
	GROUP BY product_version_id, signature_id
) as tcbs_r;

RETURN TRUE;
END; $f$;

-- now create a backfill function 
-- so that we can backfill missing data
CREATE OR REPLACE FUNCTION backfill_tcbs_ranking(
	updateday DATE )
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$f$
BEGIN

DELETE FROM tcbs_ranking WHERE report_date = updateday;
PERFORM update_tcbs_ranking(updateday, false);

RETURN TRUE;
END; $f$;




