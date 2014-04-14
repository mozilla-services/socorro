
CREATE OR REPLACE VIEW product_selector AS
    SELECT product_versions.product_name, product_versions.version_string, 'new'::text AS which_table, product_versions.version_sort FROM product_versions WHERE (now() <= product_versions.sunset_date) ORDER BY product_versions.product_name, product_versions.version_string;

ALTER TABLE product_selector OWNER TO breakpad_rw;
