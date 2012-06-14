/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

-- function

CREATE OR REPLACE FUNCTION update_adu (
	updateday date )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
AS $f$
BEGIN
-- daily batch update procedure to update the
-- adu-product matview, used to power graphs
-- gets its data from raw_adu, which is populated
-- daily by metrics

-- check if raw_adu has been updated.  otherwise, abort.
PERFORM 1 FROM raw_adu
WHERE "date" = updateday
LIMIT 1;

IF NOT FOUND THEN
	RAISE EXCEPTION 'raw_adu not updated for %',updateday;
END IF;

-- check if ADU has already been run for the date

PERFORM 1 FROM product_adu
WHERE adu_date = updateday LIMIT 1;

IF FOUND THEN
	RAISE EXCEPTION 'update_adu has already been run for %', updateday;
END IF;

-- insert releases

INSERT INTO product_adu ( product_version_id, os_name,
		adu_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
	updateday,
	coalesce(sum(raw_adu.adu_count), 0)
FROM product_versions
	LEFT OUTER JOIN raw_adu
		ON product_versions.product_name = raw_adu.product_name
		AND product_versions.version_string = raw_adu.product_version
		AND product_versions.build_type ILIKE raw_adu.build_channel
		AND raw_adu.date = updateday
	LEFT OUTER JOIN os_name_matches
    	ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type = 'release'
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
        ON product_versions.product_name = raw_adu.product_name
        AND product_versions.release_version = raw_adu.product_version
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
GROUP BY productdims_id, os;

RETURN TRUE;
END; $f$;

-- backfill adu

DO $f$
DECLARE aduday DATE;
BEGIN
FOR aduday IN SELECT i
	-- time-limited version for stage/dev
	-- FROM generate_series(timestamp '2011-07-20', timestamp '2011-07-27', '1 day') as gs(i)
	FROM generate_series(timestamp '2011-04-17', '2011-08-13', '1 day') as gs(i)
	LOOP

    DELETE FROM product_adu WHERE adu_date = aduday;
	PERFORM update_adu(aduday);

END LOOP;
END;$f$;







