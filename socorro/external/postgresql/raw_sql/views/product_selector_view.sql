CREATE VIEW product_selector AS
    SELECT product_versions.product_name, product_versions.version_string, 'new'::text AS which_table, product_versions.version_sort, product_versions.has_builds, product_versions.is_rapid_beta FROM product_versions WHERE (now() <= product_versions.sunset_date) ORDER BY product_versions.product_name, product_versions.version_string
;
