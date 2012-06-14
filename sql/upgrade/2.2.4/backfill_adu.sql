/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

-- function

CREATE OR REPLACE FUNCTION backfill_adu (
	updateday date, forproduct text default '' )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
AS $f$
DECLARE myproduct CITEXT := forproduct::citext;
BEGIN
-- stored procudure to delete and replace one day of
-- product_adu, optionally only for a specific product
-- intended to be called by backfill_matviews

-- check if raw_adu has been updated.  otherwise, warn
PERFORM 1 FROM raw_adu
WHERE "date" = updateday
LIMIT 1;

IF NOT FOUND THEN
	RAISE INFO 'raw_adu not updated for %',updateday;
END IF;

-- delete rows to be replaced

DELETE FROM product_adu
USING product_versions
WHERE adu_date = updateday
AND product_adu.product_version_id = product_versions.product_version_id
AND ( product_name = myproduct OR myproduct = '' );

DELETE FROM product_adu
USING productdims
WHERE adu_date = updateday
AND product_adu.product_version_id = productdims.id
AND ( product = myproduct OR myproduct = '' );

-- insert releases

INSERT INTO product_adu ( product_version_id, os_name,
		adu_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
	updateday,
	coalesce(sum(raw_adu.adu_count), 0)
FROM product_versions
	LEFT OUTER JOIN raw_adu
		ON product_versions.product_name = raw_adu.product_name::citext
		AND product_versions.version_string = raw_adu.product_version::citext
		AND product_versions.build_type ILIKE raw_adu.build_channel::citext
		AND raw_adu.date = updateday
	LEFT OUTER JOIN os_name_matches
    	ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type = 'release'
        AND ( product_versions.product_name = myproduct OR myproduct = '' )
GROUP BY product_version_id, os;

-- insert betas
-- does not include any missing beta counts; should resolve that later

INSERT INTO product_adu ( product_version_id, os_name,
        adu_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
    updateday,
    coalesce(sum(raw_adu.adu_count), 0)
FROM product_versions
    JOIN raw_adu
        ON product_versions.product_name = raw_adu.product_name::citext
        AND product_versions.release_version = raw_adu.product_version::citext
        AND raw_adu.date = updateday
    JOIN os_name_matches
    	ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type = 'Beta'
        AND raw_adu.build_channel = 'beta'
        AND EXISTS ( SELECT 1
            FROM product_version_builds
            WHERE product_versions.product_version_id = product_version_builds.product_version_id
              AND product_version_builds.build_id = build_numeric(raw_adu.build)
            )
        AND ( product_versions.product_name = myproduct OR myproduct = '' )
GROUP BY product_version_id, os;

-- insert old products

INSERT INTO product_adu ( product_version_id, os_name,
        adu_date, adu_count )
SELECT productdims_id, coalesce(os_name,'Unknown') as os,
	updateday, coalesce(sum(raw_adu.adu_count),0)
FROM productdims
	JOIN product_visibility ON productdims.id = product_visibility.productdims_id
	LEFT OUTER JOIN raw_adu
		ON productdims.product = raw_adu.product_name
		AND productdims.version = raw_adu.product_version
		AND raw_adu.date = updateday
    LEFT OUTER JOIN os_name_matches
    	ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
WHERE updateday BETWEEN ( start_date - interval '1 day' )
	AND ( end_date + interval '1 day' )
    AND ( product = myproduct OR myproduct = '' )
GROUP BY productdims_id, os;

RETURN TRUE;
END; $f$;


