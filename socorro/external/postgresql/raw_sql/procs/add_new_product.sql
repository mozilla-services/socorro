CREATE OR REPLACE FUNCTION add_new_product(
    prodname text,
    initversion major_version,
    prodid text DEFAULT NULL::text,
    ftpname text DEFAULT NULL::text,
    release_throttle numeric DEFAULT 1.0,
    rapid_beta_version numeric DEFAULT 999.0
)
    RETURNS boolean
    LANGUAGE plpgsql
AS $$
DECLARE current_sort int;
        rel_name text;
BEGIN

IF prodname IS NULL OR initversion IS NULL THEN
    RAISE NOTICE 'a product name and initial version are required';
    RETURN FALSE;
END IF;

-- check if product already exists
PERFORM 1 FROM products
WHERE product_name = prodname;

IF FOUND THEN
        RAISE INFO 'product % is already in the database', prodname;
        RETURN FALSE;
END IF;

-- add the product
SELECT max(sort) INTO current_sort
FROM products;

INSERT INTO products ( product_name, sort, rapid_release_version,
        release_name, rapid_beta_version )
VALUES ( prodname, current_sort + 1, initversion,
        COALESCE(ftpname, prodname), rapid_beta_version);

-- add the release channels

INSERT INTO product_build_types ( product_name, build_type )
WITH build_types AS (
    select enumlabel as build_type
    from pg_catalog.pg_enum WHERE enumtypid = 'build_type'::regtype
)
SELECT prodname, build_type
FROM build_types;

-- if throttling, change throttle for release versions

IF release_throttle < 1.0 THEN

        UPDATE product_build_types
        SET throttle = release_throttle
        WHERE product_name = prodname
                AND build_type = 'release';

END IF;

-- add the productid map

IF prodid IS NOT NULL THEN
        INSERT INTO product_productid_map ( product_name,
                productid, version_began )
        VALUES ( prodname, prodid, initversion );
END IF;

RETURN TRUE;

END;
$$;
