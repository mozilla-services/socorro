\set ON_ERROR_STOP 1

create or replace function to_major_version(
	version text )
returns major_version
language sql immutable as $f$
-- turns a version string into a major version
-- i.e. "6.0a2" into "6.0"
SELECT substring($1 from $x$^(\d+\.\d+)$x$)::major_version;
$f$;


