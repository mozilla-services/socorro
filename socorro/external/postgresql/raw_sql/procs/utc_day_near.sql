CREATE OR REPLACE FUNCTION utc_day_near(timestamp with time zone, timestamp without time zone) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $_$
select $1 > ( $2 AT TIME ZONE 'UTC' - INTERVAL '1 day' )
AND $1 < ( $2 AT TIME ZONE 'UTC' + INTERVAL '2 days' )
$_$;


