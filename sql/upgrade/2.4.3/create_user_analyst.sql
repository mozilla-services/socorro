\set ON_ERROR_STOP 1

DO $f$
BEGIN
	PERFORM 1 FROM pg_user WHERE usename = 'analyst';
	
	IF NOT FOUND THEN
		CREATE ROLE analyst LOGIN CONNECTION LIMIT 10;
	
	END IF;
END; $f$;

ALTER USER analyst SET statement_timeout = '15min';
ALTER USER analyst SET work_mem = '128MB';
ALTER USER analyst SET temp_buffers = '128MB';

 GRANT SELECT ON TABLE addresses TO analyst;
 GRANT SELECT ON TABLE bug_associations TO analyst;
 GRANT SELECT ON TABLE bugs TO analyst;
 GRANT SELECT ON TABLE correlation_addons TO analyst;
 GRANT SELECT ON TABLE correlation_cores TO analyst;
 GRANT SELECT ON TABLE correlation_modules TO analyst;
 GRANT SELECT ON TABLE correlations TO analyst;
 GRANT SELECT ON TABLE daily_crash_codes TO analyst;
 GRANT SELECT ON TABLE daily_crashes TO analyst;
 GRANT SELECT ON TABLE daily_hangs TO analyst;
 GRANT SELECT ON TABLE domains TO analyst;
 GRANT SELECT ON TABLE extensions TO analyst;
 GRANT SELECT ON TABLE flash_versions TO analyst;
 GRANT SELECT ON TABLE frames TO analyst;
 GRANT SELECT ON TABLE jobs TO analyst;
 GRANT SELECT ON TABLE os_names TO analyst;
 GRANT SELECT ON TABLE os_versions TO analyst;
 GRANT SELECT ON TABLE plugins TO analyst;
 GRANT SELECT ON TABLE plugins_reports TO analyst;
 GRANT SELECT ON TABLE process_types TO analyst;
 GRANT SELECT ON TABLE product_adu TO analyst;
 GRANT SELECT ON TABLE product_productid_map TO analyst;
 GRANT SELECT ON TABLE product_release_channels TO analyst;
 GRANT SELECT ON TABLE product_version_builds TO analyst;
 GRANT SELECT ON TABLE product_versions TO analyst;
 GRANT SELECT ON TABLE products TO analyst;
 GRANT SELECT ON TABLE rank_compare TO analyst;
 GRANT SELECT ON TABLE raw_adu TO analyst;
 GRANT SELECT ON TABLE reasons TO analyst;
 GRANT SELECT ON TABLE release_channels TO analyst;
 GRANT SELECT ON TABLE releases_raw TO analyst;
 GRANT SELECT ON TABLE reports_bad TO analyst;
 GRANT SELECT ON TABLE reports_clean TO analyst;
 GRANT SELECT ON TABLE reports_duplicates TO analyst;
 GRANT SELECT ON TABLE signature_bugs_rollup TO analyst;
 GRANT SELECT ON TABLE signature_build TO analyst;
 GRANT SELECT ON TABLE signature_products TO analyst;
 GRANT SELECT ON TABLE signature_products_rollup TO analyst;
 GRANT SELECT ON TABLE signatures TO analyst;
 GRANT SELECT ON TABLE socorro_db_version TO analyst;
 GRANT SELECT ON TABLE special_product_platforms TO analyst;
 GRANT SELECT ON TABLE tcbs TO analyst;
 GRANT SELECT ON TABLE uptime_levels TO analyst;
 GRANT SELECT ON TABLE windows_versions TO analyst;

-- grant per-column permissions to analyst
DO $f$
DECLARE colnames TEXT;
	tabname TEXT;
BEGIN

FOR tabname, colnames IN 
	SELECT table_name, 
		array_to_string(array_agg(column_name::text),',')
	FROM information_schema.columns
	WHERE table_name IN ( 'reports', 'reports_user_info' )
	AND column_name NOT IN ( 'email', 'url' ) 
	GROUP BY table_name LOOP
	
	EXECUTE 'GRANT SELECT ( ' || colnames || ' ) ON TABLE ' || tabname
		|| ' to analyst;';
		
END LOOP;

END; $f$;



