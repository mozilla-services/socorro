CREATE OR REPLACE FUNCTION nonzero_string(citext) RETURNS boolean
    LANGUAGE sql
    AS $_$
SELECT btrim($1) <> '' AND $1 IS NOT NULL;
$_$;


CREATE OR REPLACE FUNCTION nonzero_string(text) RETURNS boolean
    LANGUAGE sql
    AS $_$
SELECT btrim($1) <> '' AND $1 IS NOT NULL;
$_$;


