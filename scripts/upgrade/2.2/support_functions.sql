\SET ON_ERROR_STOP = 1

-- a large set of small functions which help with date calculations
-- version string conversion, and similar tasks.

create or replace function build_date (
	build_id numeric )
returns date
language sql immutable strict as $f$
-- converts build number to a date
SELECT to_date(substr( $1::text, 1, 8 ),'YYYYMMDD');
$f$;

create or replace function major_version(
	version text )
returns major_version
language sql immutable strict as $f$
-- turns a version string into a major version
-- i.e. "6.0a2" into "6.0"
SELECT substring($1 from $x$^(\d+.\d+)$x$);
$f$;

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

create or replace function major_version_sort(
	version text )
returns text
language sql immutable strict as $f$
-- converts a major_version string into a padded, 
-- sortable string
select version_sort_digit( substring($1 from $x$^(\d+)$x$) )
	|| version_sort_digit( substring($1 from $x$^\d+\.(\d+)$x$) );
$f$;

create or replace function sunset_date (
	build_id numeric, build_type citext )
returns date
language sql immutable as $f$
-- sets a sunset date for visibility
-- based on a build number
-- current spec is 18 weeks for releases
-- 9 weeks for everything else
select ( build_date($1) +
	case when $2 = 'release'
		then interval '18 weeks'
	else
		interval '9 weeks'
	end ) :: date
$f$;

create or replace function utc_day_begins_pacific (
	date )
returns timestamp
language sql
immutable strict as $f$
-- does the tricky date math of converting a UTC date
-- into a Pacfic timestamp without time zone
-- for the beginning of the day
SELECT $1::timestamp without time zone at time zone 'Etc/UTC' at time zone 'America/Los_Angeles';
$f$;

create or replace function utc_day_ends_pacific (
	date )
returns timestamp
language sql
immutable strict as $f$
-- does the tricky date math of converting a UTC date
-- into a Pacfic timestamp without time zone
-- for the end of the day
SELECT ( $1::timestamp without time zone at time zone 'Etc/UTC' at time zone 'America/Los_Angeles' ) + interval '1 day'
$f$;
	
create or replace function build_numeric (
	varchar )
returns numeric
language sql immutable strict
as $f$
-- safely converts a build number to a numeric type
-- if the build is not a number, returns NULL
SELECT CASE WHEN $1 ~ $x$^\d+$$x$ THEN
	$1::numeric
ELSE
	NULL::numeric
END;
$f$;
	
