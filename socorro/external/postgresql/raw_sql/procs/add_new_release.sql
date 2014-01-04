CREATE OR REPLACE FUNCTION add_new_release(product citext, version citext, release_channel citext, build_id numeric, platform citext, beta_number integer DEFAULT NULL::integer, repository text DEFAULT 'release'::text, update_products boolean DEFAULT false, ignore_duplicates boolean DEFAULT false) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE rname citext;
BEGIN
-- adds a new release to the releases_raw table
-- to be picked up by update_products later
-- does some light format validation

-- check for NULLs, blanks
IF NOT ( nonzero_string(product) AND nonzero_string(version)
	AND nonzero_string(release_channel) and nonzero_string(platform)
	AND build_id IS NOT NULL ) THEN
	RAISE NOTICE 'product, version, release_channel, platform and build ID are all required';
    RETURN FALSE;
END IF;

-- product
-- what we get could be a product name or a release name.  depending, we want to insert the
-- release name
SELECT release_name INTO rname
FROM products WHERE release_name = product;
IF rname IS NULL THEN
	SELECT release_name INTO rname
	FROM products WHERE product_name = product;
	IF rname IS NULL THEN
		RAISE NOTICE 'You must supply a valid product or product release name';
        RETURN FALSE;
	END IF;
END IF;

--validate channel
PERFORM validate_lookup('release_channels','release_channel',release_channel,'release channel');
--validate build
IF NOT ( build_date(build_id) BETWEEN '2005-01-01'
	AND (current_date + INTERVAL '1 month') ) THEN
	RAISE NOTICE 'invalid buildid';
    RETURN FALSE;
END IF;

--add row
--duplicate check will occur in the EXECEPTION section
INSERT INTO releases_raw (
	product_name, version, platform, build_id,
	build_type, beta_number, repository )
VALUES ( rname, version, platform, build_id,
	lower(release_channel), beta_number, repository );

--call update_products, if desired
IF update_products THEN
	PERFORM update_product_versions();
END IF;

--return
RETURN TRUE;

--exception clause, mainly catches duplicate rows.
EXCEPTION
	WHEN UNIQUE_VIOLATION THEN
		IF ignore_duplicates THEN
			RETURN FALSE;
		ELSE
			RAISE NOTICE 'the release you have entered is already present in he database';
            RETURN FALSE;
		END IF;
END;$$;


