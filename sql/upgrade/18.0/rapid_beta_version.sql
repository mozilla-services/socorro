\set ON_ERROR_STOP 1

-- add rapid_beta_version benchmark to products
-- only happening to Firefox right now
SELECT add_column_if_not_exists('products','rapid_beta_version','major_version');

UPDATE products SET rapid_beta_version = '16.0'
WHERE product_name = 'Firefox';

UPDATE products SET rapid_beta_version = '1000.0'
WHERE product_name <> 'Firefox';

-- we're merging camino into newTCBS
UPDATE products SET rapid_release_version = '2.1'
WHERE product_name = 'Camino';

-- add new columns to product_versions and populate them
DO $$
BEGIN

PERFORM 1 FROM information_schema.columns
WHERE table_name = 'product_versions'
	AND column_name = 'has_builds';

IF NOT FOUND THEN

	ALTER TABLE product_versions
	ADD COLUMN has_builds BOOLEAN DEFAULT FALSE,
	ADD COLUMN is_rapid_beta BOOLEAN DEFAULT FALSE,
	ADD COLUMN rapid_beta_id INT REFERENCES product_versions(product_version_id);

	UPDATE product_versions SET has_builds = TRUE
	WHERE build_type IN ( 'aurora', 'nightly' )
		AND product_name = 'Firefox'
		AND major_version_sort(major_version) >= major_version_sort('16.0');

END IF;
END;$$;