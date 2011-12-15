\set ON_ERROR_STOP 1

BEGIN;

SELECT try_lock_table('reports');

SELECT add_column_if_not_exists('reports','productid',
$x$ALTER TABLE reports ADD COLUMN productid TEXT;$x$);

COMMIT;