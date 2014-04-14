CREATE OR REPLACE FUNCTION backfill_home_page_graph(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM home_page_graph WHERE report_date = updateday;
PERFORM update_home_page_graph(updateday, false, check_period);

RETURN TRUE;
END; $$;


