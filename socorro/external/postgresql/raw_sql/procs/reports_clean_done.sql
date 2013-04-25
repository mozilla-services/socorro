CREATE OR REPLACE FUNCTION reports_clean_done(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
-- this function checks that reports_clean has been updated
-- all the way to the last hour of the UTC day
BEGIN

PERFORM 1
    FROM reports_clean
    WHERE date_processed BETWEEN ( ( updateday::timestamp at time zone 'utc' )
            +  ( interval '24 hours' - check_period ) )
        AND ( ( updateday::timestamp at time zone 'utc' ) + interval '1 day' )
    LIMIT 1;
IF FOUND THEN
    RETURN TRUE;
ELSE
    RETURN FALSE;
END IF;
END; $$;


