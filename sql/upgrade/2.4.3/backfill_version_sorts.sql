\set ON_ERROR_STOP 1

UPDATE productdims SET version_sort = old_version_sort(version);

UPDATE product_versions SET version_sort = version_sort(release_version, beta_number);

ANALYZE productdims;
ANALYZE product_versions;