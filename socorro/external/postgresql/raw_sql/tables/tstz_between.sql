CREATE FUNCTION tstz_between(tstz timestamp with time zone, bdate date, fdate date) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT $1 >= ( $2::timestamp AT TIME ZONE 'UTC' ) 
	AND $1 < ( ( $3 + 1 )::timestamp AT TIME ZONE 'UTC' );
$_$;


