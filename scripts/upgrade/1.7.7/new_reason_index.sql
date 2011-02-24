DO $f$
DECLARE part_name TEXT;
	part_week TIMESTAMP := '2010-06-07';
BEGIN
	set maintenance_work_mem = '1GB';
	
	WHILE part_week < now() LOOP 
		part_name := 'reports_' || to_char(part_week,'YYYYMMDD');
		EXECUTE 'CREATE INDEX ' || part_name || '_reason ON ' 
			|| part_name || '(reason);';
		part_week := part_week + INTERVAL '7 days';
	END LOOP;
END;$f$;
	