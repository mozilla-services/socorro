\set ON_ERROR_STOP 1

BEGIN;

SELECT try_lock_table('reports');

ALTER TABLE reports ADD COLUMN productid TEXT;

COMMIT;