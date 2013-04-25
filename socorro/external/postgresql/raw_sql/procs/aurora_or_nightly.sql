CREATE OR REPLACE FUNCTION aurora_or_nightly(version text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
-- figures out "aurora" or "nightly" from a version string
-- returns ERROR otherwise
SELECT CASE WHEN $1 LIKE '%a1' THEN 'nightly'
	WHEN $1 LIKE '%a2' THEN 'aurora'
	ELSE 'ERROR' END;
$_$;


