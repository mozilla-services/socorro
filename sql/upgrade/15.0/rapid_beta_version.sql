\set ON_ERROR_STOP 1

SELECT add_column_if_not_exists('products','rapid_beta_version','major_version');

UPDATE products SET rapid_beta_version = '16.0'
WHERE product_name = 'Firefox';

UPDATE products SET rapid_beta_version = '1000.0'
WHERE product_name <> 'Firefox';

UPDATE products SET rapid_release_version = '2.1'
WHERE product_name = 'Camino';