\set ON_ERROR_STOP 1

create or replace function old_version_sort(
	vers text ) 
returns text
language sql
immutable 
as $f$
SELECT to_char( matched[1]::int, 'FM000' )
	|| to_char( matched[2]::int, 'FM000' )
	|| CASE WHEN matched[3] = 'b' THEN 'b'
		ELSE 'z' END
	|| '000'
	|| to_char( coalesce( matched[4]::int, 0 ), 'FM000' )
FROM ( SELECT regexp_matches($1, $x$^(\d+)[^\d]*\.(\d+)(b?)[^\.]*(?:\.(\d+))*$x$) as matched) as match 
LIMIT 1;
$f$;

UPDATE productdims SET version_sort = old_version_sort(version);

