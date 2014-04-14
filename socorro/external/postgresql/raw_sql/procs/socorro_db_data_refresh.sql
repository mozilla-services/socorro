CREATE OR REPLACE FUNCTION socorro_db_data_refresh(refreshtime timestamp with time zone DEFAULT NULL::timestamp with time zone) RETURNS timestamp with time zone
    LANGUAGE sql
    AS $_$
UPDATE socorro_db_version SET refreshed_at = COALESCE($1, now())
RETURNING refreshed_at;
$_$;


