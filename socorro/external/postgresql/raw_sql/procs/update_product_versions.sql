CREATE OR REPLACE FUNCTION update_product_versions(
    product_window integer DEFAULT 30
)
    RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET maintenance_work_mem TO '512MB'
AS $$
BEGIN

-- Daily batch update function for new products and versions
-- Reads data from releases_raw, cleans it
-- and puts the new versions into product_versions 
-- and product_version_builds

-- Cumulative and can be run repeatedly without issues
-- * covers FennecAndroid and ESR releases
-- * Compares releases from the last 30 days
-- * Restricts to only the defined "repositories" in 
--   release_repositories
-- * covers WebRT
-- * covers Rapid betas
-- * covers Final betas

-- Create a temporary table of products and raw release data
-- * Rename products described in special_product_platforms
-- * Detect rapid beta products
-- * Filter out any products not coming from release_repositories
--   or not defined in products table
create temporary table releases_recent
ON commit drop
AS
select COALESCE ( specials.product_name, products.product_name )
        AS product_name,
    releases_raw.version,
    releases_raw.beta_number,
    releases_raw.build_id,
    releases_raw.update_channel,
    releases_raw.platform,
    (major_version_sort(version) >= major_version_sort(rapid_release_version))
        AS is_rapid,
    is_rapid_beta(releases_raw.update_channel, version, rapid_beta_version::major_version)
        AS is_rapid_beta,
    releases_raw.repository,
    releases_raw.version_build
FROM releases_raw
    JOIN products ON releases_raw.product_name = products.release_name
    JOIN release_repositories
        ON releases_raw.repository = release_repositories.repository
    LEFT OUTER JOIN special_product_platforms AS specials
        ON releases_raw.platform::citext = specials.platform
        AND releases_raw.product_name = specials.release_name
        AND releases_raw.repository = specials.repository
        AND releases_raw.update_channel = specials.release_channel
        AND major_version_sort(version) >= major_version_sort(min_version)
WHERE
    build_date(build_id) > (current_date - product_window)
    AND version_matches_channel(releases_raw.version,
        releases_raw.update_channel::citext);

-- fix ESR versions

UPDATE releases_recent
SET update_channel = 'esr'
WHERE update_channel ILIKE 'release'
    AND version ILIKE '%esr';

-- Insert WebRT "releases", which are copies of Firefox releases,
-- only if the FF release is greater than the first release for WebRT

INSERT INTO releases_recent (
    product_name,
    version,
    beta_number,
    build_id,
    update_channel,
    platform,
    is_rapid,
    is_rapid_beta,
    repository
)
SELECT 'WebappRuntime',
    version,
    beta_number,
    build_id,
    update_channel,
    platform,
    is_rapid,
    is_rapid_beta,
    repository
FROM releases_recent
    JOIN products
        ON products.product_name = 'WebappRuntime'
WHERE releases_recent.product_name = 'Firefox'
    AND major_version_sort(releases_recent.version)
        >= major_version_sort(products.rapid_release_version);

-- Insert WebRTmobile "releases", which are copies of Fennec releases,
-- only if the Fennec release is greater than the first release for WebRTmobile

INSERT INTO releases_recent (
    product_name,
    version,
    beta_number,
    build_id,
    update_channel,
    platform,
    is_rapid,
    is_rapid_beta,
    repository
)
SELECT 'WebappRuntimeMobile',
    version,
    beta_number,
    build_id,
    update_channel,
    platform,
    is_rapid,
    is_rapid_beta,
    repository
FROM releases_recent
    JOIN products
        ON products.product_name = 'WebappRuntimeMobile'
WHERE releases_recent.product_name = 'Fennec'
    AND major_version_sort(releases_recent.version)
        >= major_version_sort(products.rapid_release_version);

-- Insert MetroFirefox "releases", which are copies of Firefox releases,
-- only if the FF release is greater than the first release for MetroFirefox

INSERT INTO releases_recent (
    product_name,
    version,
    beta_number,
    build_id,
    update_channel,
    platform,
    is_rapid,
    is_rapid_beta,
    repository
)
SELECT
    'MetroFirefox' as product_name,
    version,
    beta_number,
    build_id,
    update_channel,
    platform,
    is_rapid,
    is_rapid_beta,
    repository
FROM releases_recent
    JOIN products
     ON products.product_name = 'MetroFirefox'
WHERE releases_recent.product_name = 'Firefox'
    AND major_version_sort(releases_recent.version)
        >= major_version_sort(products.rapid_release_version);

-- Release metadata for B2G does not come from releases_raw
-- Partner data is inserted into update_channel_map instead

INSERT INTO releases_recent (
    product_name,
    version,
    beta_number,
    build_id,
    update_channel,
    platform,
    is_rapid,
    is_rapid_beta,
    repository
)
SELECT 'B2G' as product_name,
    version,
    null as beta_number,
    build as build_id,
    json_object_field_text(rewrite, 'rewrite_build_type_to') as update_channel,
    -- TODO this should really be "gonk"
    'Android' as platform,
    'true' as is_rapid,
    'false' as is_rapid_beta,
    json_object_field_text(rewrite, 'Android_Manufacturer') as repository
FROM raw_update_channels
JOIN update_channel_map USING (update_channel)
WHERE build IN
    (SELECT trim(both '"' from value::text)::numeric
     FROM json_array_elements(rewrite->'BuildID'))
AND first_report > (current_date - product_window);

-- Put collected data into product_versions
-- First releases, aurora and nightly and non-rapid betas

insert into product_versions (
    product_name,
    major_version,
    release_version,
    version_string,
    beta_number,
    version_sort,
    build_date,
    sunset_date,
    build_type,
    has_builds,
    build_type_enum
)
select releases_recent.product_name,
    to_major_version(version),
    version,
    version_string(version, releases_recent.beta_number),
    releases_recent.beta_number,
    version_sort(version, releases_recent.beta_number),
    build_date(min(build_id)),
    sunset_date(min(build_id), releases_recent.update_channel),
    releases_recent.update_channel::citext,
    (releases_recent.update_channel IN ('aurora', 'nightly')),
    releases_recent.update_channel::build_type_enum as build_type_enum
from releases_recent
    left outer join product_versions ON
        ( releases_recent.product_name = product_versions.product_name
            AND releases_recent.version = product_versions.release_version
            AND releases_recent.beta_number IS NOT DISTINCT FROM product_versions.beta_number )
where is_rapid
    AND product_versions.product_name IS NULL
    AND NOT releases_recent.is_rapid_beta
    AND update_channel IS NOT NULL
group by releases_recent.product_name, version,
    releases_recent.beta_number,
    releases_recent.update_channel::citext, releases_recent.update_channel;

-- Insert rapid betas "parent" products
-- These will have a product, but no builds

insert into product_versions (
    product_name,
    major_version,
    release_version,
    version_string,
    beta_number,
    version_sort,
    build_date,
    sunset_date,
    build_type,
    is_rapid_beta,
    has_builds,
    build_type_enum
)
select products.product_name,
    to_major_version(version),
    version,
    version || 'b',
    0,
    version_sort(version, 0),
    build_date(min(build_id)),
    sunset_date(min(build_id), 'beta' ),
    'beta',
    TRUE,
    TRUE,
    'beta'
from releases_recent
    join products ON releases_recent.product_name = products.release_name
    left outer join product_versions ON
        ( releases_recent.product_name = product_versions.product_name
            AND releases_recent.version = product_versions.release_version
            AND product_versions.beta_number = 0 )
where is_rapid
    and releases_recent.is_rapid_beta
    and product_versions.product_name IS NULL
group by products.product_name, version;

-- Add individual betas for rapid_betas
-- These need to get linked to their master rapid_beta

insert into product_versions (
    product_name,
    major_version,
    release_version,
    version_string,
    beta_number,
    version_sort,
    build_date,
    sunset_date,
    build_type,
    rapid_beta_id,
    build_type_enum
)
select products.product_name,
    to_major_version(version),
    version,
    version_string(version, releases_recent.beta_number),
    releases_recent.beta_number,
    version_sort(version, releases_recent.beta_number),
    build_date(min(build_id)),
    rapid_parent.sunset_date,
    'beta',
    rapid_parent.product_version_id,
    'beta'
from releases_recent
    join products ON releases_recent.product_name = products.release_name
    left outer join product_versions ON
        ( releases_recent.product_name = product_versions.product_name
            AND releases_recent.version = product_versions.release_version
            AND product_versions.beta_number = releases_recent.beta_number )
    join product_versions as rapid_parent ON
        releases_recent.version = rapid_parent.release_version
        and releases_recent.product_name = rapid_parent.product_name
        and rapid_parent.is_rapid_beta
where is_rapid
    and releases_recent.is_rapid_beta
    and product_versions.product_name IS NULL
group by products.product_name, version, rapid_parent.product_version_id,
    releases_recent.beta_number, rapid_parent.sunset_date;

-- Insert product build ids
-- * Rapid beta parent records will have no buildids of their own

insert into product_version_builds
(product_version_id, build_id, platform, repository)
select distinct product_versions.product_version_id,
        releases_recent.build_id,
        releases_recent.platform,
        releases_recent.repository
from releases_recent
    join product_versions
        ON releases_recent.product_name = product_versions.product_name
        AND releases_recent.version = product_versions.release_version
        AND releases_recent.update_channel = product_versions.build_type
        AND ( releases_recent.beta_number IS NOT DISTINCT FROM product_versions.beta_number )
    left outer join product_version_builds ON
        product_versions.product_version_id = product_version_builds.product_version_id
        AND releases_recent.build_id = product_version_builds.build_id
        AND releases_recent.platform = product_version_builds.platform
where product_version_builds.product_version_id is null;

drop table releases_recent;

RETURN TRUE;
END;
$$;
