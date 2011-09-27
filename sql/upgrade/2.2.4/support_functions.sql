\set ON_ERROR_STOP = 1

-- more support functions, now adjusted to support aurora and nightlies

create or replace function version_string(
	version text, beta_number int
) returns text
language sql immutable as $f$
-- converts a stripped version and a beta number
-- into a version string
SELECT CASE WHEN $2 <> 0 THEN
	$1 || 'b' || $2
ELSE
	$1
END;
$f$;

create or replace function version_string(
	version text, beta_number int, channel text
) returns text
language sql immutable as $f$
-- converts a stripped version and a beta number
-- into a version string
SELECT CASE WHEN $2 <> 0 THEN
	$1 || 'b' || $2
WHEN $3 ILIKE 'nightly' THEN
	$1 || 'a1'
WHEN $3 ILIKE 'aurora' THEN
	$1 || 'a2'
ELSE
	$1
END;
$f$;

create or replace function version_number_elements(
	version_string text )
returns text[]
language SQL immutable as $f$
-- breaks up the parts of a version string
-- into an array of elements
select regexp_matches($1,$x$^(\d+)\.(\d+)([a-zA-Z]?)(\d*)\.?(\d*)$x$);
$f$;

create or replace function version_number_elements(
	version text,  beta_number int )
returns text[]
language SQL as $f$
-- breaks up the parts of a version string into an
-- array of elements.  if a beta number is present
-- includes that
select case when $2 <> 0 then
	   regexp_matches($1,$x$^(\d+)\.(\d+)$x$) || ARRAY [ 'b', $2::text, '' ]
    else
       regexp_matches($1,$x$^(\d+)\.(\d+)([a-zA-Z]?)(\d*)\.?(\d*)$x$)
    end;
$f$;

create or replace function version_number_elements(
	version text,  beta_number int, channel text )
returns text[]
language SQL as $f$
-- breaks up the parts of a version string into an
-- array of elements.  if a beta number is present
-- includes that
select case when $3 ilike 'beta' AND $2 <> 0 then
	   regexp_matches($1,$x$^(\d+)\.(\d+)$x$) || ARRAY [ 'b', $2::text, '' ]
	when $3 ilike 'nightly' then
	   regexp_matches($1,$x$^(\d+)\.(\d+)$x$) || ARRAY [ 'a', '1', '' ]
	when $3 ilike 'aurora' then
	   regexp_matches($1,$x$^(\d+)\.(\d+)$x$) || ARRAY [ 'a', '2', '' ]
    else
       regexp_matches($1,$x$^(\d+)\.(\d+)([a-zA-Z]?)(\d*)\.?(\d*)$x$)
    end;
$f$;

create or replace function version_sort_digit (
	digit text )
returns text
language sql immutable as $f$
-- converts an individual part of a version number
-- into a three-digit sortable string
SELECT CASE WHEN $1 <> '' THEN
	to_char($1::INT,'FM000')
	ELSE '000' END;
$f$;

create or replace function version_sort(
	version_string text )
returns text
language sql immutable as $f$
-- converts a version string into a padded
-- sortable string
select version_sort_digit(vne[1])
	|| version_sort_digit(vne[2])
	|| CASE WHEN vne[3] = '' THEN 'z' ELSE vne[3] END
	|| version_sort_digit(vne[4])
	|| version_sort_digit(vne[5])
from ( select version_number_elements($1) as vne ) as vne;
$f$;

create or replace function version_sort(
	version text, beta_number int )
returns text
language sql immutable as $f$
-- converts a version string with a beta number
-- into a padded
-- sortable string
select version_sort_digit(vne[1])
	|| version_sort_digit(vne[2])
	|| CASE WHEN vne[3] = '' THEN 'z' ELSE vne[3] END
	|| version_sort_digit(vne[4])
	|| version_sort_digit(vne[5])
from ( select version_number_elements($1, $2) as vne ) as vne;
$f$;

create or replace function version_sort(
	version text, beta_number int, channel text )
returns text
language sql immutable as $f$
-- converts a version string with a beta number
-- into a padded
-- sortable string
select version_sort_digit(vne[1])
	|| version_sort_digit(vne[2])
	|| CASE WHEN vne[3] = '' THEN 'z' ELSE vne[3] END
	|| version_sort_digit(vne[4])
	|| version_sort_digit(vne[5])
from ( select version_number_elements($1, $2, $3) as vne ) as vne;
$f$;

CREATE OR REPLACE FUNCTION aurora_or_nightly(
	version text )
returns text
language sql immutable strict as $f$
-- figures out "aurora" or "nightly" from a version string
-- returns ERROR otherwise
SELECT CASE WHEN $1 LIKE '%a1' THEN 'nightly'
	WHEN $1 LIKE '%a2' THEN 'aurora'
	ELSE 'ERROR' END;
$f$;
