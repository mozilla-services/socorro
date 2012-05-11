\set ON_ERROR_STOP 1

CREATE OR REPLACE FUNCTION edit_featured_versions (
	product citext,
	VARIADIC featured_versions text[]
)
RETURNS boolean
LANGUAGE plpgsql
AS $f$
-- this function allows admins to change the featured versions
-- for a particular product
BEGIN

--check required parameters
IF NOT ( nonzero_string(product) AND nonzero_string(featured_versions[1]) ) THEN
	RAISE EXCEPTION 'a product name and at least one version are required';
END IF;

--check that all versions are not expired
SELECT 1 FROM product_verstions
WHERE product_name = product
  AND version_string = ANY ( featured_versions )
  AND sunset_date < current_date;
IF FOUND THEN
	RAISE EXCEPTION 'one or more of the versions you have selected is already expired';
END IF;

--Remove disfeatured versions
UPDATE product_versions SET featured_version = false
WHERE featured_version
	AND NOT ( version_string = ANY( featured_versions ) );
	
--feature new versions
UPDATE product_versions SET featured_version = true
WHERE version_string = ANY ( featured_versions )
	AND NOT featured_version;

RETURN TRUE;

END;$f$;
