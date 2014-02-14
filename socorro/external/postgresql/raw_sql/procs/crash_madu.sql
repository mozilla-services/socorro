CREATE OR REPLACE FUNCTION crash_madu(crashes bigint, adu numeric, throttle numeric DEFAULT 1.0) RETURNS numeric
    LANGUAGE sql
    AS $_$
SELECT CASE WHEN $2 = 0 THEN 0::numeric
ELSE
	round( ( $1 * 10^6::numeric / $2 ) / $3, 3)
END;
$_$;

