
DO $f$
DECLARE rc_part TEXT;
BEGIN
	SET maintenance_work_mem = '512MB';

	FOR rc_part IN SELECT relname FROM pg_stat_user_tables
		WHERE relname LIKE 'reports_clean_2011%'
		ORDER BY relname
		LOOP
		
		EXECUTE 'CREATE INDEX ' || rc_part || '_sig_prod_date'
			|| ' ON ' || rc_part || '( signature_id, product_version_id, date_processed);';
			
		RAISE INFO 'index created on %',rc_part;
			
	END LOOP;
	
END;$f$;