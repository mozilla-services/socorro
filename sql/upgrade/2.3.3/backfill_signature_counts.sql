create or replace function backfill_signature_counts (
	begindate date, enddate date )
returns boolean
language plpgsql
as $f$
DECLARE thisdate DATE := begindate;
BEGIN

WHILE thisdate <= enddate LOOP

	DELETE FROM os_signature_counts WHERE report_date = updateday;
	DELETE FROM product_signature_counts WHERE report_date = updateday;
	DELETE FROM uptime_signature_counts WHERE report_date = updateday;
	PERFORM update_os_signature_counts(updateday, false);
	PERFORM update_product_signature_counts(updateday, false);
	PERFORM update_uptime_signature_counts(updateday, false);
	
	thisdate := thisdate + 1;
	
END LOOP;

RETURN TRUE;
END; $f$;