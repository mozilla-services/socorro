CREATE OR REPLACE FUNCTION plugin_count_state(running_count integer, process_type citext, crash_count integer) RETURNS integer
    LANGUAGE sql IMMUTABLE
    AS $_$
-- allows us to do a plugn count horizontally
-- as well as vertically on tcbs
SELECT CASE WHEN $2 = 'plugin' THEN
  coalesce($3,0) + $1
ELSE
  $1
END; $_$;


CREATE AGGREGATE plugin_count(citext, integer) (
    SFUNC = plugin_count_state,
    STYPE = integer,
    INITCOND = '0'
);
