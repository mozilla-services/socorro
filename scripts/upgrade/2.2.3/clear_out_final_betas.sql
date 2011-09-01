\set ON_ERROR_STOP 1

BEGIN;

-- drop the final betas

DELETE FROM product_version_builds
USING product_versions
WHERE beta_number = 999;

PERFORM update_product_versions();

END;

BEGIN;

-- redo all tcbs and graphs from the beta(final) release

SELECT backfill_matviews('2011-06-14');

END;

BEGIN;

-- now we should be able to delete final betas which aren't valid

DELETE FROM product_versions
WHERE beta_number = 999
AND NOT EXISTS (SELECT 1 FROM product_versions as releases
	WHERE releases.build_type = 'release'
		AND releases.major_version = product_versions.major_version
		AND releases.product_name = product_versions.product_name );
		
END;