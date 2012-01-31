\set ON_ERROR_STOP 1

ALTER TABLE reports_clean ADD architecture CITEXT;
ALTER TABLE reports_clean ADD cores INT;

DO $f$
DECLARE thisweek DATE;
	weekstring TEXT;
BEGIN 

thisweek := '2012-01-09';

WHILE thisweek < current_date LOOP

	RAISE INFO 'populating cpu data for week %',thisweek;

	weekstring := to_char(thisweek, 'YYYYMMDD');
	
	EXECUTE 'UPDATE reports_clean_' || weekstring || '
		SET architecture = cpu_name,
		cores = get_cores(cpu_info)
	FROM reports_' || weekstring || ' as reports
	WHERE reports.uuid = reports_clean_' || weekstring || '.uuid
		AND reports_clean_' || weekstring || '.date_processed > ''2011-12-23''
		AND reports.date_processed > ''2011-12-23'' ';

	thisweek := thisweek + 7;
	
END LOOP;

END;$f$;

VACUUM ANALYZE reports_clean_20120109;
VACUUM ANALYZE reports_clean_20120116;
VACUUM ANALYZE reports_clean_20120123;

DO $f$
DECLARE thisweek DATE;
	weekstring TEXT;
BEGIN 

thisweek := '2012-01-09';

WHILE thisweek < current_date LOOP

	RAISE INFO 'creating index on arch for week %',thisweek;

	weekstring := 'reports_clean_' || to_char(thisweek, 'YYYYMMDD');
	
	EXECUTE 'CREATE INDEX ' || weekstring || '_architecture_cores'

	thisweek := thisweek + 7;
	
END LOOP;

END;$f$;