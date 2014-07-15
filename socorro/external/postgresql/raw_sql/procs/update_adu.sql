CREATE OR REPLACE FUNCTION update_adu(
    updateday date,
    checkdata boolean DEFAULT true
)
    RETURNS boolean
    LANGUAGE plpgsql
AS $$
BEGIN
-- daily batch update procedure to update the
-- adu-product matview, used to power graphs
-- gets its data from raw_adi, which is populated
-- daily by the fetch-adi-from-hive crontabber job

-- check if raw_adi has been updated.  otherwise, abort.
PERFORM 1 FROM raw_adi
WHERE "date" = updateday
LIMIT 1;

IF NOT FOUND THEN
    RAISE EXCEPTION 'raw_adi not updated for %', updateday;
END IF;

-- check if ADU has already been run for the date
PERFORM 1 FROM product_adu
WHERE adu_date = updateday LIMIT 1;
IF FOUND THEN
  IF checkdata THEN
      RAISE NOTICE 'update_adu has already been run for %', updateday;
  END IF;
  RETURN FALSE;
END IF;

-- insert releases
-- note that we're now matching against product_guids were we can
-- and that we need to strip the {} out of the guids

INSERT INTO product_adu ( product_version_id, os_name,
        adu_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
    updateday,
    coalesce(sum(adi_count), 0)
FROM product_versions
    LEFT OUTER JOIN (
        SELECT COALESCE(prodmap.product_name, raw_adi.product_name)::citext
                as product_name,
            raw_adi.product_version::citext as product_version,
            raw_adi.update_channel as update_channel,
            raw_adi.adi_count,
            os_name_matches.os_name
        FROM raw_adi
        LEFT OUTER JOIN product_productid_map as prodmap
            ON raw_adi.product_guid = btrim(prodmap.productid, '{}')
        LEFT OUTER JOIN os_name_matches
            ON raw_adi.product_os_platform ILIKE os_name_matches.match_string
        WHERE raw_adi.date = updateday
        ) as prod_adu
        ON product_versions.product_name = prod_adu.product_name
        AND product_versions.version_string = prod_adu.product_version
        AND product_versions.build_type_enum::text = prod_adu.update_channel
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type_enum IN ('release','nightly','aurora')
GROUP BY product_version_id, os;

-- insert ESRs
-- need a separate query here because the ESR version number doesn't match

INSERT INTO product_adu ( product_version_id, os_name,
        adu_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
    updateday,
    coalesce(sum(adi_count), 0)
FROM product_versions
    LEFT OUTER JOIN (
        SELECT COALESCE(prodmap.product_name, raw_adi.product_name)::citext
            as product_name, raw_adi.product_version::citext as product_version,
            raw_adi.update_channel as update_channel,
            raw_adi.adi_count,
            os_name_matches.os_name
        FROM raw_adi
        LEFT OUTER JOIN product_productid_map as prodmap
            ON raw_adi.product_guid = btrim(prodmap.productid, '{}')
        LEFT OUTER JOIN os_name_matches
            ON raw_adi.product_os_platform ILIKE os_name_matches.match_string
        WHERE raw_adi.date = updateday
            and raw_adi.update_channel ILIKE 'esr'
        ) as prod_adu
        ON product_versions.product_name = prod_adu.product_name
        AND product_versions.version_string
            =  ( prod_adu.product_version || 'esr' )
        AND product_versions.build_type_enum::text = prod_adu.update_channel
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type_enum = 'esr'
GROUP BY product_version_id, os;

-- insert betas

INSERT INTO product_adu ( product_version_id, os_name,
        adu_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
    updateday,
    coalesce(sum(adi_count), 0)
FROM product_versions
    JOIN products USING ( product_name )
    LEFT OUTER JOIN (
        SELECT COALESCE(prodmap.product_name, raw_adi.product_name)::citext
                as product_name,
            raw_adi.product_version::citext as product_version,
            raw_adi.update_channel as update_channel,
            raw_adi.adi_count,
            os_name_matches.os_name,
            build_numeric(raw_adi.build) as build_id
        FROM raw_adi
        LEFT OUTER JOIN product_productid_map as prodmap
            ON raw_adi.product_guid = btrim(prodmap.productid, '{}')
        LEFT OUTER JOIN os_name_matches
            ON raw_adi.product_os_platform ILIKE os_name_matches.match_string
        WHERE raw_adi.date = updateday
            AND raw_adi.update_channel = 'beta'
        ) as prod_adu
        ON product_versions.product_name = prod_adu.product_name
        AND product_versions.release_version = prod_adu.product_version
        AND product_versions.build_type_enum::text = prod_adu.update_channel
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type_enum = 'beta'
        AND EXISTS ( SELECT 1
            FROM product_version_builds
            WHERE product_versions.product_version_id = product_version_builds.product_version_id
              AND product_version_builds.build_id = prod_adu.build_id
            )
GROUP BY product_version_id, os;

RETURN TRUE;
END;
$$;
