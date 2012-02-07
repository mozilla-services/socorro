\set ON_ERROR_STOP 1

DO $f$
DECLARE cronjoblist TEXT[];
	arrinc INT := 1;
BEGIN

-- daily cronjobs
cronjoblist := ARRAY[ 'update_product_versions','update_signatures',
	'update_os_versions', 'update_tcbs', 'update_adu',
	'update_daily_crashes', 'update_hang_report' ];
	
-- loop through list, initializing each cronjob which doesn't yet exist	
WHILE cronjoblist[arrinc] IS NOT NULL LOOP

	PERFORM 1 FROM cronjobs WHERE cronjob = 'dailyMatviews:' || cronjoblist[arrinc];
	
	IF NOT FOUND THEN
	
		INSERT INTO cronjobs ( cronjob, frequency, lag )
		VALUES ( 'dailyMatviews:' || cronjoblist[arrinc], '1 day', '0 days' );
		
	END IF;
	
	arrinc := arrinc + 1;
	
END LOOP;

END;$f$;
