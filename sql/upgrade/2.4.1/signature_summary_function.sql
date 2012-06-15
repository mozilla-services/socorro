\set ON_ERROR_STOP 1

CREATE TYPE signature_summary AS (
	category text,
	report_count int,
	percent numeric
);


CREATE OR REPLACE FUNCTION signature_summary (
	sig TEXT, report_type TEXT, days INT, 
	product TEXT, versions INT[] DEFAULT '{}'
	)
RETURNS SETOF signature_summary
LANGUAGE plpgsql
SET TIMEZONE = 'UTC'
AS
$f$
DECLARE begin_date TEXT;
	query_string TEXT;
	extra_join TEXT := ' ';
	first_col TEXT;
	first_col_format TEXT := 'category';
	version_search TEXT := ' ';
	sigid INT;
BEGIN
-- returns a signature summary based on the given
-- parameters.  

-- format date
begin_date := to_char( now() - ( days * INTERVAL '1 day' ), 'YYYY-MM-DD' );

-- check if versions are supplied, if so create string
IF versions <> '{}' AND report_type <> 'products' THEN

	version_search := ' AND reports_clean.product_version_id IN ( '
		|| array_to_string(versions, ',') || ' ) ';
		
END IF;

-- look up signature ID
SELECT signature_id INTO sigid
FROM signatures 
WHERE signature = sig;

-- create query snippets by type of report
CASE report_type
	WHEN 'products' THEN
		-- do nothing, we'll handle this special case later
		NULL;
	WHEN 'uptime' THEN
		first_col := 'uptime_string';
		extra_join := ' JOIN uptime_levels ON reports_clean.uptime >= min_uptime ' ||
			'AND reports_clean.uptime < max_uptime ';
	WHEN 'os' THEN
		first_col := 'os_version_string';
		extra_join := ' JOIN os_versions USING ( os_version_id ) ';
	WHEN 'process_type' THEN
		first_col := 'process_type';
	WHEN 'flash_version' THEN
		first_col := 'flash_version';
		first_col_format := $q$CASE WHEN category = '' THEN 'Unknown/No Flash' ELSE category END $q$;
		extra_join := ' LEFT OUTER JOIN flash_versions USING (flash_version_id) ';
	ELSE
		RAISE EXCEPTION 'report type % is not defined',report_type;
END CASE;

-- create the query string
IF report_type = 'products' THEN
	-- products report is different because it takes all
	-- products, not just the ones selected
	query_string := $q$
	WITH counts AS (
		SELECT product_version_id, product_name, version_string,
			count(*) AS report_count
		FROM reports_clean
			JOIN product_versions USING (product_version_id)
		WHERE 
			signature_id = $q$ || sigid || $q$
			AND date_processed >= $q$ || quote_literal(begin_date) || $q$ 
			AND date_processed < $q$ || quote_literal(now()::text) || $q$
		GROUP BY product_version_id, product_name, version_string
	),
	totals as (
		SELECT product_version_id, product_name, version_string, 
			report_count, 
			sum(report_count) OVER () as total_count
		FROM counts
	)
	SELECT product_name || ' ' || version_string, 
		report_count::INT, 
		round((report_count * 100::numeric)/total_count,3) as percentage
	FROM totals
	ORDER BY report_count DESC;
	$q$;

ELSE
	query_string := $q$
	WITH counts AS (
		SELECT $q$ || first_col || $q$ as category, count(*) AS report_count
		FROM reports_clean
			JOIN product_versions USING (product_version_id) $q$
			|| extra_join || $q$ 
		WHERE 
			signature_id = $q$ || sigid || $q$
			AND date_processed >= $q$ || quote_literal(begin_date) || $q$ 
			AND date_processed < $q$ || quote_literal(now()::text) || $q$
			AND product_name = $q$ || quote_literal(product)
			|| version_search ||
		$q$ GROUP BY $q$ || first_col || $q$
	),
	totals as (
		SELECT category, report_count, 
			sum(report_count) OVER () as total_count
		FROM counts
	)
	SELECT $q$ || first_col_format || $q$::text, 
		report_count::INT, 
		round((report_count::numeric)/total_count,5) as percentage
	FROM totals
	ORDER BY report_count DESC;
	$q$;
END IF;

RAISE INFO 'search query is: %',query_string;

RETURN QUERY EXECUTE query_string;

RETURN;

END;$f$;




	




