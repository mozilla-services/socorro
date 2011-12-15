\set ON_ERROR_STOP 1

SELECT create_column_if_not_exists( 'raw_adu', 'product_guid', $x$
ALTER TABLE raw_adu ADD COLUMN product_guid TEXT;
$x$);