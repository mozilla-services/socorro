\set ON_ERROR_STOP 1

CREATE OR REPLACE FUNCTION get_cores(
	cpudetails TEXT )
RETURNS INT
IMMUTABLE
LANGUAGE sql
AS $f$
SELECT substring($1 from $x$\| (\d+)$$x$)::INT;
$f$;
