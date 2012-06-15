create or replace function utc_day_is (
	timestamptz, timestamp )
returns boolean
language sql
immutable as
$f$
select $1 >= ( $2 AT TIME ZONE 'UTC' )
	AND $1 < ( ( $2 + INTERVAL '1 day' ) AT TIME ZONE 'UTC'  );
$f$;

create or replace function utc_day_ends_pacific (
	date )
returns timestamp
language sql
immutable as $f$
-- does the tricky date math of converting a UTC date
-- into a Pacfic timestamp without time zone
-- for the end of the day
SELECT ( ( $1 + 1 )::timestamp without time zone at time zone 'Etc/UTC' at time zone 'America/Los_Angeles' )
$f$;

create or replace function tstz_between(
	tstz timestamp with time zone, bdate date, fdate date)
returns boolean
language sql
immutable
as $f$
SELECT $1 >= ( $2::timestamp AT TIME ZONE 'UTC' ) 
	AND $1 < ( ( $3 + 1 )::timestamp AT TIME ZONE 'UTC' );
$f$;