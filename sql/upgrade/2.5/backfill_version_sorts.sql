\set ON_ERROR_STOP 1

UPDATE product_versions SET version_sort = version_sort(release_version, beta_number);

ANALYZE product_versions;