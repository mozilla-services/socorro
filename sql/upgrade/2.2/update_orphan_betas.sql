/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */


CREATE OR REPLACE FUNCTION update_final_betas (
    updateday date )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
AS $f$
BEGIN
-- this function adds "final" beta releases to the list of
-- products from the reports table
-- since the first time we see them would be in the
-- reports table

-- create a temporary table including all builds found

create temporary table orphan_betas
on commit drop as
select build_numeric(build) as build_id,
  version, product, os_name,
  count(*) as report_count
from reports
where date_processed BETWEEN utc_day_begins_pacific(updateday)
  AND utc_day_ends_pacific(updateday)
  AND release_channel = 'beta'
  and os_name <> ''
  and build ~ $x$^20\d{12}$$x$
  and version !~ $x$[a-zA-Z]$x$
group by build, version, product, os_name;

-- insert release versions into the betas

INSERT INTO orphan_betas
SELECT build_id, release_version, product_name, platform
FROM product_versions JOIN product_version_builds
  USING (product_version_id)
WHERE build_type = 'release';

-- purge all builds we've already seen

DELETE FROM orphan_betas
USING product_versions JOIN product_version_builds
  USING (product_version_id)
WHERE orphan_betas.product = product_versions.product_name
  AND orphan_betas.version = product_versions.release_version
  AND orphan_betas.build_id = product_version_builds.build_id
  AND product_versions.build_type <> 'release';

-- purge builds which are lower than an existing beta

DELETE FROM orphan_betas
USING product_versions JOIN product_version_builds
  USING (product_version_id)
WHERE orphan_betas.product = product_versions.product_name
  AND orphan_betas.version = product_versions.release_version
  AND orphan_betas.build_id < ( product_version_builds.build_id)
  AND product_versions.beta_number between 1 and 998
  AND product_versions.build_type = 'beta';

-- purge builds which are higher than a release

DELETE FROM orphan_betas
USING product_versions JOIN product_version_builds
  USING (product_version_id)
WHERE orphan_betas.product = product_versions.product_name
  AND orphan_betas.version = product_versions.release_version
  AND orphan_betas.build_id > ( product_version_builds.build_id + 2000000 )
  AND product_versions.build_type = 'release';

-- purge unused versions

DELETE FROM orphan_betas
WHERE product NOT IN (SELECT product_name
    FROM products
    WHERE major_version_sort(orphan_betas.version)
      >= major_version_sort(products.rapid_release_version) );

-- if no bfinal exists in product_versions, then create one

INSERT INTO product_versions (
    product_name,
    major_version,
    release_version,
    version_string,
    beta_number,
    version_sort,
    build_date,
    sunset_date,
    build_type)
SELECT product,
  major_version(version),
  version,
  version || '(beta)',
  999,
  version_sort(version, 999),
  build_date(min(orphan_betas.build_id)),
  sunset_date(min(orphan_betas.build_id), 'beta'),
  'Beta'
FROM orphan_betas
  JOIN products ON orphan_betas.product = products.product_name
  LEFT OUTER JOIN product_versions
    ON orphan_betas.product = product_versions.product_name
    AND orphan_betas.version = product_versions.release_version
    AND product_versions.beta_number = 999
WHERE product_versions.product_name IS NULL
GROUP BY product, version;

-- add the buildids to product_version_builds
INSERT INTO product_version_builds (product_version_id, build_id, platform)
SELECT product_version_id, orphan_betas.build_id, os_name
FROM product_versions JOIN orphan_betas
  ON product_name = product
  AND product_versions.release_version = orphan_betas.version
WHERE beta_number = 999;

RETURN TRUE;

END; $f$;

-- now backfill

DO $f$
DECLARE tcdate DATE;
    enddate DATE;
BEGIN

tcdate := '2011-04-17';
enddate := '2011-08-09';
-- timelimited version for stage/dev
--tcdate := '2011-07-25';
--enddate := '2011-08-09';

WHILE tcdate < enddate LOOP

    PERFORM update_final_betas(tcdate);
    RAISE INFO 'orphan betas updated for %',tcdate;
    DROP TABLE orphan_betas;
    tcdate := tcdate + 5;

END LOOP;
END; $f$;


