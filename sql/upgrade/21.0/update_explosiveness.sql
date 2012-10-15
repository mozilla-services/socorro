\set ON ERROR STOP 1

BEGIN; 

CREATE OR REPLACE FUNCTION public.update_explosiveness(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval)
 RETURNS boolean
 LANGUAGE plpgsql
 SET work_mem TO '512MB'
 SET temp_buffers TO '512MB'
 SET client_min_messages TO 'ERROR'
AS $function$
-- set stats parameters per Kairo
DECLARE
	-- minimum crashes/mil.adu to show up
	minrate INT := 10;
	-- minimum comparitor figures if there are no
	-- or very few proir crashes to smooth curves
	-- mostly corresponds to Kairo "clampperadu"
	mindiv_one INT := 30;
	mindiv_three INT := 15;
	mes_edate DATE;
	mes_b3date DATE;
	comp_e1date DATE;
	comp_e3date DATE;
	comp_bdate DATE;
BEGIN
-- this function populates a daily matview
-- for explosiveness
-- depends on tcbs and product_adu

-- check if we've been run
IF checkdata THEN
	PERFORM 1 FROM explosiveness
	WHERE last_date = updateday
	LIMIT 1;
	IF FOUND THEN
		RAISE INFO 'explosiveness has already been run for %.',updateday;
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

-- check if product_adu and tcbs are updated
PERFORM 1
FROM tcbs JOIN product_adu
   ON tcbs.report_date = product_adu.adu_date
WHERE tcbs.report_date = updateday
LIMIT 1;

IF NOT FOUND THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Either product_adu or tcbs have not been updated to the end of %',updateday;
	ELSE
		RAISE NOTICE 'Either product_adu or tcbs has not been updated, skipping.';
		RETURN TRUE;
	END IF;
END IF;

-- compute dates
-- note that dates are inclusive
-- last date of measured period
mes_edate := updateday;
-- first date of the measured period for 3-day
mes_b3date := updateday - 2;
-- last date of the comparison period for 1-day
comp_e1date := updateday - 1;
-- last date of the comparison period for 3-day
comp_e3date := mes_b3date - 1;
-- first date of the comparison period
comp_bdate := mes_edate - 9;

-- create temp table with all of the crash_madus for each
-- day, including zeroes
CREATE TEMPORARY TABLE crash_madu
ON COMMIT DROP
AS
WITH crashdates AS (
	SELECT report_date::DATE as report_date
	FROM generate_series(comp_bdate, mes_edate, INTERVAL '1 day')
		AS gs(report_date)
),
adusum AS (
	SELECT adu_date, sum(adu_count) as adu_count,
		( mindiv_one * 1000000::numeric / sum(adu_count)) as mindivisor,
		product_version_id
	FROM product_adu
	WHERE adu_date BETWEEN comp_bdate and mes_edate
		AND adu_count > 0
	GROUP BY adu_date, product_version_id
),
reportsum AS (
	SELECT report_date, sum(report_count) as report_count,
		product_version_id, signature_id
	FROM tcbs
	WHERE report_date BETWEEN comp_bdate and mes_edate
	GROUP BY report_date, product_version_id, signature_id
),
crash_madu_raw AS (
	SELECT ( report_count * 1000000::numeric ) / adu_count AS crash_madu,
		reportsum.product_version_id, reportsum.signature_id,
		report_date, mindivisor
	FROM adusum JOIN reportsum
		ON adu_date = report_date
		AND adusum.product_version_id = reportsum.product_version_id
),
product_sigs AS (
	SELECT DISTINCT product_version_id, signature_id
	FROM crash_madu_raw
)
SELECT crashdates.report_date,
	coalesce(crash_madu, 0) as crash_madu,
	product_sigs.product_version_id, product_sigs.signature_id,
	COALESCE(crash_madu_raw.mindivisor, 0) as mindivisor
FROM crashdates CROSS JOIN product_sigs
	LEFT OUTER JOIN crash_madu_raw
	ON crashdates.report_date = crash_madu_raw.report_date
		AND product_sigs.product_version_id = crash_madu_raw.product_version_id
		AND product_sigs.signature_id = crash_madu_raw.signature_id;

-- create crosstab with days1-10
-- create the multiplier table

CREATE TEMPORARY TABLE xtab_mult
ON COMMIT DROP
AS
SELECT report_date,
	( case when report_date = mes_edate THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day0,
	( case when report_date = ( mes_edate - 1 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day1,
	( case when report_date = ( mes_edate - 2 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day2,
	( case when report_date = ( mes_edate - 3 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day3,
	( case when report_date = ( mes_edate - 4 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day4,
	( case when report_date = ( mes_edate - 5 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day5,
	( case when report_date = ( mes_edate - 6 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day6,
	( case when report_date = ( mes_edate - 7 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day7,
	( case when report_date = ( mes_edate - 8 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day8,
	( case when report_date = ( mes_edate - 9 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day9
	FROM generate_series(comp_bdate, mes_edate, INTERVAL '1 day')
		AS gs(report_date);

-- create the crosstab
CREATE TEMPORARY TABLE crash_xtab
ON COMMIT DROP
AS
SELECT product_version_id, signature_id,
	round(SUM ( crash_madu * day0 ),2) AS day0,
	round(SUM ( crash_madu * day1 ),2) AS day1,
	round(SUM ( crash_madu * day2 ),2) AS day2,
	round(SUM ( crash_madu * day3 ),2) AS day3,
	round(SUM ( crash_madu * day4 ),2) AS day4,
	round(SUM ( crash_madu * day5 ),2) AS day5,
	round(SUM ( crash_madu * day6 ),2) AS day6,
	round(SUM ( crash_madu * day7 ),2) AS day7,
	round(SUM ( crash_madu * day8 ),2) AS day8,
	round(SUM ( crash_madu * day9 ),2) AS day9
FROM xtab_mult
	JOIN crash_madu USING (report_date)
GROUP BY product_version_id, signature_id;

-- create oneday temp table
CREATE TEMPORARY TABLE explosive_oneday
ON COMMIT DROP
AS
WITH sum1day AS (
	SELECT product_version_id, signature_id, crash_madu as sum1day,
		mindivisor
	FROM crash_madu
	WHERE report_date = mes_edate
	AND crash_madu > 10
),
agg9day AS (
	SELECT product_version_id, signature_id,
		AVG(crash_madu) AS avg9day,
		MAX(crash_madu) as max9day
	FROM crash_madu
	WHERE report_date BETWEEN comp_bdate and comp_e1date
	GROUP BY product_version_id, signature_id
)
SELECT sum1day.signature_id,
	sum1day.product_version_id ,
	round (
		( sum1day.sum1day - coalesce(agg9day.avg9day,0) )
			/
		GREATEST ( agg9day.max9day - agg9day.avg9day, sum1day.mindivisor )
		, 2 )
	as explosive_1day,
	round(sum1day,2) as oneday_rate
FROM sum1day
	LEFT OUTER JOIN agg9day USING ( signature_id, product_version_id )
WHERE sum1day.sum1day IS NOT NULL;

ANALYZE explosive_oneday;

-- create threeday temp table
CREATE TEMPORARY TABLE explosive_threeday
ON COMMIT DROP
AS
WITH avg3day AS (
	SELECT product_version_id, signature_id,
        AVG(crash_madu) as avg3day,
		AVG(mindivisor) as mindivisor
	FROM crash_madu
	WHERE report_date BETWEEN mes_b3date and mes_edate
	GROUP BY product_version_id, signature_id
	HAVING AVG(crash_madu) > 10
),
agg7day AS (
	SELECT product_version_id, signature_id,
		SUM(crash_madu)/7 AS avg7day,
		COALESCE(STDDEV(crash_madu),0) AS sdv7day
	FROM crash_madu
	WHERE report_date BETWEEN comp_bdate and comp_e3date
	GROUP BY product_version_id, signature_id
)
SELECT avg3day.signature_id,
	avg3day.product_version_id ,
	round (
		( avg3day - coalesce(avg7day,0) )
			/
		GREATEST ( sdv7day, avg3day.mindivisor )
		, 2 )
	as explosive_3day,
	round(avg3day, 2) as threeday_rate
FROM avg3day LEFT OUTER JOIN agg7day
	USING ( signature_id, product_version_id );

ANALYZE explosive_threeday;

-- truncate explosiveness
DELETE FROM explosiveness;

-- merge the two tables and insert
INSERT INTO explosiveness (
	last_date, signature_id, product_version_id,
	oneday, threeday,
	day0, day1, day2, day3, day4,
	day5, day6, day7, day8, day9)
SELECT updateday, signature_id, product_version_id,
	explosive_1day, explosive_3day,
	day0, day1, day2, day3, day4,
	day5, day6, day7, day8, day9
FROM crash_xtab
	LEFT OUTER JOIN explosive_oneday
	USING ( signature_id, product_version_id )
	LEFT OUTER JOIN explosive_threeday
	USING ( signature_id, product_version_id )
WHERE explosive_1day IS NOT NULL or explosive_3day IS NOT NULL
ORDER BY product_version_id;

RETURN TRUE;
END; $function$
;

-- Get rid of old definition
DROP FUNCTION public.update_explosiveness(date, boolean);
