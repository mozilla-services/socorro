CREATE OR REPLACE FUNCTION week_begins_partition(partname text) RETURNS timestamp with time zone
    LANGUAGE sql IMMUTABLE
    SET "TimeZone" TO 'UTC'
    AS $_$
SELECT to_timestamp( substring($1 from $x$\d+$$x$), 'YYYYMMDD' );
$_$;


