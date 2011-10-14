create or replace function backfill_reports_clean (
	begin_time timestamptz, end_time timestamptz )
returns boolean 
language plpgsql as
$f$
-- administrative utility for backfilling reports_clean to the selected date
-- intended to be called on the command line
-- uses a larger cycle (6 hours) if we have to backfill several days of data
-- note that this takes timestamptz as parameters
-- otherwise call backfill_reports_clean_by_date
DECLARE cyclesize INTERVAL := '1 hour';
	stop_time timestamptz := end_time;
	cur_time timestamptz := begin_time;
BEGIN
	IF ( end_time - begin_time ) > interval '12 hours' THEN
		cyclesize := '6 hours';
	END IF;
	
	WHILE cur_time < stop_time LOOP
		IF cur_time + cyclesize > stop_time THEN
			cyclesize = stop_time - cur_time;
		END IF;
		
		RAISE INFO 'backfilling % of reports_clean starting at %',cyclesize,cur_time;
		
		DELETE FROM reports_clean 
		WHERE date_processed >= cur_time 
			AND date_processed < ( cur_time + cyclesize );
		
		DELETE FROM reports_user_info
		WHERE date_processed >= cur_time 
			AND date_processed < ( cur_time + cyclesize );
		
		PERFORM update_reports_clean( cur_time, cyclesize, true );
		
		cur_time := cur_time + cyclesize;
	END LOOP;
	
	RETURN TRUE;
END;$f$;

CREATE OR REPLACE FUNCTION backfill_reports_clean_by_date (
	starts DATE, ends DATE )
returns boolean
language sql as
$f$
SELECT backfill_reports_clean( $1::timestamp AT TIME ZONE 'UTC',
	$2::timestamp AT TIME ZONE 'UTC' );
$f$;


