CREATE OR REPLACE FUNCTION old_version_sort(vers text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT to_char( matched[1]::int, 'FM000' )
	|| to_char( matched[2]::int, 'FM000' )
	|| to_char( coalesce( matched[4]::int, 0 ), 'FM000' )
	|| CASE WHEN matched[3] <> '' THEN 'b'
		WHEN matched[5] <> '' THEN 'b'
		ELSE 'z' END
	|| '000'
FROM ( SELECT regexp_matches($1,
$x$^(\d+)[^\d]*\.(\d+)([a-z]?)[^\.]*(?:\.(\d+))?([a-z]?).*$$x$) as matched) as match 
LIMIT 1;
$_$;


