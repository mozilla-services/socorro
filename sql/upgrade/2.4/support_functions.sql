\set ON_ERROR_STOP 1

create or replace function week_begins_partition (
	partname text )
returns timestamptz
language sql
set timezone = 'UTC'
as $f$
SELECT to_timestamp( substring($1 from $x$\d+$$x$), 'YYYYMMDD' );
$f$;

create or replace function week_ends_partition (
	partname text )
returns timestamptz
language sql
set timezone = 'UTC'
as $f$
SELECT to_timestamp( substring($1 from $x$\d+$$x$), 'YYYYMMDD' ) + INTERVAL '7 days';
$f$;

create or replace function week_begins_partition_string (
	partname text )
returns text
language sql
set timezone = 'UTC'
as $f$
SELECT to_char( week_begins_partition( $1 ), 'YYYY-MM-DD' ) || ' 00:00:00 UTC';
$f$;


create or replace function week_ends_partition_string (
	partname text )
returns text
language sql
set timezone = 'UTC'
as $f$
SELECT to_char( week_ends_partition( $1 ), 'YYYY-MM-DD' ) || ' 00:00:00 UTC';
$f$;