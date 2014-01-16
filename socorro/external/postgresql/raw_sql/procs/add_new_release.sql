CREATE OR REPLACE FUNCTION add_new_release(
        product citext,
        version citext,
        update_channel citext,
        build_id numeric,
        platform citext,
        beta_number integer DEFAULT NULL::integer,
        repository text DEFAULT 'release'::text,
        update_products boolean DEFAULT false,
        ignore_duplicates boolean DEFAULT false
        -- TODO Add beta_id for weird ass betas
    )
    RETURNS boolean
    LANGUAGE plpgsql
AS $$
DECLARE
    rname citext;
    nrows integer;
BEGIN
-- adds a new release to the releases_raw table
-- to be picked up by update_products later
-- does some light format validation

-- check for NULLs, blanks
IF NOT
    ( nonzero_string(product)
      AND nonzero_string(version)
      AND nonzero_string(update_channel)
      AND nonzero_string(platform)
      AND build_id IS NOT NULL )
THEN
    RAISE NOTICE 'product, version, update_channel, build_id and platform are all required';
    RETURN FALSE;
END IF;

-- product
-- what we get could be a product name or a release name.  depending, we want to insert the
-- release name
SELECT release_name INTO rname FROM products WHERE release_name = product;
IF rname IS NULL THEN
    SELECT release_name INTO rname FROM products WHERE product_name = product;
    IF rname IS NULL THEN
        RAISE NOTICE 'You must supply a valid product or product release name.';
        RETURN FALSE;
    END IF;
END IF;

--validate channel
SELECT INTO nrows count(*) FROM pg_catalog.pg_enum
    WHERE enumtypid = 'build_type'::regtype
    AND lower(update_channel) = enumlabel;
IF nrows <= 0 THEN
    RAISE NOTICE '% is not a valid build_type', update_channel;
    RETURN FALSE;
END IF;

--validate build
IF NOT ( build_date(build_id) BETWEEN '2005-01-01'
    AND (current_date + INTERVAL '1 month') ) THEN
    RAISE NOTICE 'invalid build_id';
    RETURN FALSE;
END IF;

--add row
--duplicate check will occur in the EXECEPTION section
-- TODO add beta_id for releases that are really betas
INSERT INTO releases_raw (
    product_name, version, platform, build_id,
    update_channel, beta_number, repository, build_type
)
VALUES (
    rname, version, platform, build_id,
    lower(update_channel), beta_number, repository, lower(update_channel)
);

--call update_products, if desired
IF update_products THEN
    PERFORM update_product_versions();
END IF;

RETURN TRUE;

--exception clause, mainly catches duplicate rows.
EXCEPTION
    WHEN UNIQUE_VIOLATION THEN
        IF ignore_duplicates THEN
            RETURN FALSE;
        ELSE
            RAISE NOTICE 'The release you have entered is already present.';
            RETURN FALSE;
        END IF;
END;
$$;
