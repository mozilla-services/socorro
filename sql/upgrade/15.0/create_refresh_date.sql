\set ON_ERROR_STOP 1

SELECT add_column_if_not_exists('socorro_db_version','refreshed_at','timestamptz');

CREATE OR REPLACE FUNCTION socorro_db_data_refresh(
	refreshtime timestamptz default null )
RETURNS TIMESTAMPTZ
LANGUAGE sql AS $f$
UPDATE socorro_db_version SET refreshed_at = COALESCE($1, now())
RETURNING refreshed_at;
$f$;

SELECT socorro_db_data_refresh('2012-07-01');