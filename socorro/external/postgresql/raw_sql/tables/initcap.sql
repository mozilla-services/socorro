CREATE FUNCTION initcap(text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT upper(substr($1,1,1)) || substr($1,2);
$_$;


