CREATE FUNCTION crash_hadu(crashes bigint, adu bigint, throttle numeric DEFAULT 1.0) RETURNS numeric
    LANGUAGE sql
    AS $_$
SELECT CASE WHEN $2 = 0 THEN 0::numeric
ELSE
	round( ( $1 * 100::numeric / $2 ) / $3, 3)
END;
$_$;
