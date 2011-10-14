\set ON_ERROR_STOP 1



create or replace function update_product_versions()
returns boolean
language plpgsql
set work_mem = '512MB'
set maintenance_work_mem = '512MB'
as $f$
BEGIN
-- daily batch update function for new products and versions
-- reads data from releases_raw, cleans it
-- and puts data corresponding to the new versions into
-- product_versions and related tables

-- is cumulative and can be run repeatedly without issues
-- now includes nightly/auroras

insert into product_versions (
    product_name,
    major_version,
    release_version,
    version_string,
    beta_number,
    version_sort,
    build_date,
    sunset_date,
    build_type)
select products.product_name,
	major_version(version),
	version,
	version_string(version, releases_raw.beta_number, releases_raw.build_type),
	releases_raw.beta_number,
	version_sort(version, releases_raw.beta_number, releases_raw.build_type),
	build_date(min(build_id)),
	sunset_date(min(build_id), releases_raw.build_type ),
	releases_raw.build_type::citext
from releases_raw
	join products ON releases_raw.product_name = products.release_name
	left outer join product_versions ON
		( releases_raw.product_name = products.release_name
		    AND products.product_name = product_versions.product_name
			AND releases_raw.version = product_versions.release_version
			AND releases_raw.beta_number IS NOT DISTINCT FROM product_versions.beta_number )
where major_version_sort(version) >= major_version_sort(rapid_release_version)
	AND product_versions.product_name IS NULL
--	AND releases_raw.build_type IN ('release','beta')
group by products.product_name, version, releases_raw.beta_number, releases_raw.build_type::citext;

-- insert final betas as a copy of the release version

insert into product_versions (
    product_name,
    major_version,
    release_version,
    version_string,
    beta_number,
    version_sort,
    build_date,
    sunset_date,
    build_type)
select products.product_name,
    major_version(version),
    version,
    version || '(beta)',
    999,
    version_sort(version, 999),
    build_date(min(build_id)),
    sunset_date(min(build_id), 'beta' ),
    'beta'
from releases_raw
    join products ON releases_raw.product_name = products.release_name
    left outer join product_versions ON
        ( releases_raw.product_name = products.release_name
        	AND products.product_name = product_versions.product_name
            AND releases_raw.version = product_versions.release_version
            AND product_versions.beta_number = 999 )
where major_version_sort(version) >= major_version_sort(rapid_release_version)
    AND product_versions.product_name IS NULL
    AND releases_raw.build_type ILIKE 'release'
group by products.product_name, version;

-- add build ids

insert into product_version_builds
select distinct product_versions.product_version_id,
		releases_raw.build_id,
		releases_raw.platform
from releases_raw
	join products ON releases_raw.product_name = products.release_name
	join product_versions
		ON products.product_name = product_versions.product_name
		AND releases_raw.version = product_versions.release_version
		AND releases_raw.build_type = product_versions.build_type
		AND ( releases_raw.beta_number IS NOT DISTINCT FROM product_versions.beta_number )
	left outer join product_version_builds ON
		product_versions.product_version_id = product_version_builds.product_version_id
		AND releases_raw.build_id = product_version_builds.build_id
		AND releases_raw.platform = product_version_builds.platform
where product_version_builds.product_version_id is null;

-- add build ids for final beta

insert into product_version_builds
select distinct product_versions.product_version_id,
		releases_raw.build_id,
		releases_raw.platform
from releases_raw
	join products ON releases_raw.product_name = products.release_name
	join product_versions
		ON products.product_name = product_versions.product_name
		AND releases_raw.version = product_versions.release_version
		AND releases_raw.build_type ILIKE 'release'
		AND product_versions.beta_number = 999
	left outer join product_version_builds ON
		product_versions.product_version_id = product_version_builds.product_version_id
		AND releases_raw.build_id = product_version_builds.build_id
		AND releases_raw.platform = product_version_builds.platform
where product_version_builds.product_version_id is null;

return true;
end; $f$;
