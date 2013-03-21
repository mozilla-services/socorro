CREATE FUNCTION version_sort_digit(digit text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
-- converts an individual part of a version number
-- into a three-digit sortable string
SELECT CASE WHEN $1 <> '' THEN
	to_char($1::INT,'FM000')
	ELSE '000' END;
$_$;


