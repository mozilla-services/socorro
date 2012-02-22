\set ON_ERROR_STOP 1

SELECT backfill_reports_clean('2012-02-10', 
	date_trunc('hour', now() - interval '2 hours')); 

SELECT backfill_matviews('2012-02-10',( current_date - 1 ), false);
