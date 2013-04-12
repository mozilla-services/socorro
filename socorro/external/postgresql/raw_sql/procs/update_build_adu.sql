CREATE OR REPLACE FUNCTION update_build_adu(updateday date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET client_min_messages TO 'ERROR'
    AS $$
BEGIN
-- this function populates a daily matview
-- for **new_matview_description**
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM build_adu
    WHERE adu_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'build_adu has already been run for %.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if raw_adu is available
PERFORM 1 FROM raw_adu
WHERE "date" = updateday
LIMIT 1;
IF NOT FOUND THEN
    IF checkdata THEN
        RAISE NOTICE 'raw_adu has not been updated for %',updateday;
        RETURN FALSE;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- insert nightly, aurora
-- only 7 days of data after each build

INSERT INTO build_adu ( product_version_id, os_name,
        adu_date, build_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
    updateday,
    bdate,
    coalesce(sum(adu_count), 0)
FROM product_versions
    JOIN (
        SELECT COALESCE(prodmap.product_name, raw_adu.product_name)::citext
            as product_name, raw_adu.product_version::citext as product_version,
            raw_adu.build_channel::citext as build_channel,
            raw_adu.adu_count,
            build_date(build_numeric(raw_adu.build)) as bdate,
            os_name_matches.os_name
        FROM raw_adu
        LEFT OUTER JOIN product_productid_map as prodmap
            ON raw_adu.product_guid = btrim(prodmap.productid, '{}')
        LEFT OUTER JOIN os_name_matches
            ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
        WHERE raw_adu.date = updateday
        ) as prod_adu
        ON product_versions.product_name = prod_adu.product_name
        AND product_versions.version_string = prod_adu.product_version
        AND product_versions.build_type = prod_adu.build_channel
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type IN ('nightly','aurora')
        AND bdate is not null
        AND updateday <= ( bdate + 6 )
GROUP BY product_version_id, os, bdate;

-- insert betas
-- rapid beta parent entries only
-- only 7 days of data after each build

INSERT INTO build_adu ( product_version_id, os_name,
        adu_date, build_date, adu_count )
SELECT rapid_beta_id, coalesce(os_name,'Unknown') as os,
    updateday,
    bdate,
    coalesce(sum(adu_count), 0)
FROM product_versions
    JOIN products USING ( product_name )
    JOIN (
        SELECT COALESCE(prodmap.product_name, raw_adu.product_name)::citext
            as product_name, raw_adu.product_version::citext as product_version,
            raw_adu.build_channel::citext as build_channel,
            raw_adu.adu_count,
            os_name_matches.os_name,
            build_numeric(raw_adu.build) as build_id,
            build_date(build_numeric(raw_adu.build)) as bdate
        FROM raw_adu
        LEFT OUTER JOIN product_productid_map as prodmap
            ON raw_adu.product_guid = btrim(prodmap.productid, '{}')
        LEFT OUTER JOIN os_name_matches
            ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
        WHERE raw_adu.date = updateday
            AND raw_adu.build_channel = 'beta'
        ) as prod_adu
        ON product_versions.product_name = prod_adu.product_name
        AND product_versions.release_version = prod_adu.product_version
        AND product_versions.build_type = prod_adu.build_channel
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type = 'Beta'
        AND EXISTS ( SELECT 1
            FROM product_version_builds
            WHERE product_versions.product_version_id = product_version_builds.product_version_id
              AND product_version_builds.build_id = prod_adu.build_id
            )
        AND bdate is not null
        AND rapid_beta_id IS NOT NULL
        AND updateday <= ( bdate + 6 )
GROUP BY rapid_beta_id, os, bdate;

RETURN TRUE;
END; $$;


