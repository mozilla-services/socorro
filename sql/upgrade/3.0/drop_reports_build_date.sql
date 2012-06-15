\set ON_ERROR_STOP 1

DO $f$
BEGIN

PERFORM try_lock_table('reports','ACCESS EXCLUSIVE');

ALTER TABLE reports DROP COLUMN build_date;

END;$f$;