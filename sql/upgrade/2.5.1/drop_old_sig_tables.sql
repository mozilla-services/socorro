\set ON_ERROR_STOP 1

DROP TABLE IF EXISTS signature_first;

DROP TABLE IF EXISTS signature_build;

DROP TABLE IF EXISTS signature_productdims;

DROP FUNCTION IF EXISTS update_signature_matviews(timestamp, integer, integer);

