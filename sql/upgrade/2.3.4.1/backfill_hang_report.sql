DO $f$
DECLARE thisdate DATE;
BEGIN

	thisdate := '2011-11-16';
	
	WHILE thisdate < current_date LOOP
	
		PERFORM backfill_hang_report(thisdate);
		
		thisdate := thisdate + 1;
		
		RAISE INFO 'backfilled %',thisdate;
		
	END LOOP;
	
END; $f$;
