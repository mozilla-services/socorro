\set ON_ERROR_STOP 1

create or replace function to_major_version(
	version text )
returns major_version
language sql immutable as $f$
-- turns a version string into a major version
-- i.e. "6.0a2" into "6.0"
SELECT substring($1 from $x$^(\d+\.\d+)$x$)::major_version;
$f$;


-- new reports_clean_done, adjusts time interval for some users

begin;

drop function if exists reports_clean_done ( date );

create or replace function reports_clean_done(
    updateday date, check_period interval default interval '1 hour' )
returns boolean
language plpgsql
as $f$
-- this function checks that reports_clean has been updated
-- all the way to the last hour of the UTC day
BEGIN

PERFORM 1
    FROM reports_clean
    WHERE date_processed BETWEEN ( ( updateday::timestamp at time zone 'utc' )
            +  ( interval '24 hours' - check_period ) )
        AND ( ( updateday::timestamp at time zone 'utc' ) + interval '1 day' )
    LIMIT 1;
IF FOUND THEN
    RETURN TRUE;
ELSE
    RETURN FALSE;
END IF;
END; $f$;

commit;

create or replace function crash_hadu(
	crashes bigint, adu bigint, throttle numeric )
returns numeric as
$f$
SELECT round( ( $1 * 100::numeric / $2 ) / $3, 3);
$f$;

DO $f$
BEGIN

PERFORM 1 FROM pg_type WHERE typname = 'crash_type';

IF NOT FOUND THEN
	CREATE ENUM





