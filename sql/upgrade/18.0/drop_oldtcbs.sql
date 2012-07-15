\set ON_ERROR_STOP 1

-- drop unused tables
DROP TABLE IF EXISTS alexa_topsites CASCADE;
DROP TABLE IF EXISTS top_crashes_by_signature CASCADE;
DROP TABLE IF EXISTS top_crashes_by_url CASCADE;
DROP TABLE IF EXISTS top_crashes_by_url_signature CASCADE;
DROP TABLE IF EXISTS signature_build CASCADE;
DROP TABLE IF EXISTS signature_first CASCADE;
DROP TABLE IF EXISTS signature_bugs_rollup CASCADE;
DROP TABLE IF EXISTS signature_productdims CASCADE;
DROP TABLE IF EXISTS release_build_type_map CASCADE;
DROP TABLE IF EXISTS builds CASCADE;
DROP TABLE IF EXISTS osdims CASCADE;
DROP TABLE IF EXISTS productdims_version_sort CASCADE;
DROP TABLE IF EXISTS product_visibility CASCADE;
DROP TABLE IF EXISTS productdims CASCADE;
DROP TABLE IF EXISTS urldims CASCADE;

DROP FUNCTION IF EXISTS tokenize_version(text);
DROP LANGUAGE IF EXISTS plperl;

-- rename product version id sequence
DO $f$
BEGIN
PERFORM 1 FROM pg_class
WHERE relname = 'productdims_id_seq1';

IF FOUND THEN
	ALTER TABLE productdims_id_seq1 RENAME TO product_version_id_seq;
	ALTER TABLE product_versions ALTER COLUMN product_version_id
		SET DEFAULT NEXTVAL('product_version_id_seq');
	ALTER SEQUENCE product_version_id_seq OWNED BY product_versions.product_version_id;
END IF;
END; $f$;
