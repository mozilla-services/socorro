\set ON_ERROR_STOP 1

BEGIN;

-- delete buildids for final betas
DELETE FROM product_version_builds
USING product_versions
WHERE beta_number = 999
	AND product_versions.product_version_id = product_version_builds.product_version_id;

-- put TB, SM on rapid release
update products set rapid_release_version = '6.0' where product_name = 'Thunderbird';
update products set rapid_release_version = '2.3' where product_name = 'Seamonkey';

-- clean up some database definitions
drop index product_version_unique_beta;
create unique index product_version_unique_beta on product_versions(product_name, release_version, beta_number) WHERE beta_number IS NOT NULL;

-- make function update_final_betas a no-op
CREATE OR REPLACE FUNCTION update_final_betas(updateday date)
RETURNS BOOLEAN
LANGUAGE plpgsql AS $f$
BEGIN
	RETURN TRUE;
END; $f$;

-- repopulate products
SELECT update_product_versions();

END;

BEGIN;

-- redo all tcbs and graphs from the beta(final) release

SELECT backfill_matviews('2011-06-14');

END;

BEGIN;

-- now we should be able to delete final betas which aren't valid
CREATE TEMPORARY TABLE drop_betas ON COMMIT DROP AS
SELECT product_version_id FROM product_versions
WHERE beta_number = 999
AND NOT EXISTS (SELECT 1 FROM product_version_builds
	WHERE product_versions.product_version_id = product_version_builds.product_version_id );
	
DELETE FROM signature_products WHERE product_version_id IN 
	( SELECT product_version_id FROM drop_betas );
	
DELETE FROM tcbs WHERE product_version_id 
	IN ( SELECT product_version_id FROM drop_betas );

DELETE FROM daily_crashes WHERE productdims_id IN
	( SELECT product_version_id FROM drop_betas );
	
DELETE FROM product_adu WHERE product_version_id IN
	(SELECT product_version_id FROM drop_betas );
	
DELETE FROM product_versions WHERE product_version_id IN
	(SELECT product_version_id FROM drop_betas );
END;