\set ON_ERROR_STOP 1

-- create table of canonical release repositories for filtering
SELECT create_table_if_not_exists('release_repositories',
	$x$
	CREATE TABLE release_repositories (
		repository citext not null primary key
	);

	INSERT INTO release_repositories
	VALUES ( 'mozilla-central'), ('mozilla-1.9.2'),
            ( 'comm-central'), ('comm-1.9.2'),
            ( 'comm-central-trunk'), ('mozilla-central-android'),
            ( 'mozilla-release'), ('mozilla-beta'),
            ( 'mozilla-aurora' ), ('mozilla-aurora-android'),
            ( 'mozilla-esr10' ), ( 'mozilla-esr10-android' ),
            ( 'release' );
    $x$,'breakpad_rw');

-- add repository column to product_version_builds
SELECT add_column_if_not_exists (
	'product_version_builds','repository','citext' );

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
-- now covers FennecAndroid and ESR releases
-- now only compares releases from the last 30 days
-- now restricts to only the canonical "repositories"
-- now covers webRT
-- now covers rapid betas, but no more final betas

-- create temporary table, required because
-- all of the special cases

create temporary table releases_recent
on commit drop
as
select COALESCE ( specials.product_name, products.product_name )
		AS product_name,
	releases_raw.version,
	releases_raw.beta_number,
	releases_raw.build_id,
	releases_raw.build_type,
	releases_raw.platform,
	( major_version_sort(version) >= major_version_sort(rapid_release_version) ) as is_rapid,
    is_rapid_beta(build_type, version, rapid_beta_version) as is_rapid_beta,
	releases_raw.repository
from releases_raw
	JOIN products ON releases_raw.product_name = products.release_name
	JOIN release_repositories ON releases_raw.repository = release_repositories.repository
	LEFT OUTER JOIN special_product_platforms AS specials
		ON releases_raw.platform::citext = specials.platform
		AND releases_raw.product_name = specials.release_name
		AND releases_raw.repository = specials.repository
		AND releases_raw.build_type = specials.release_channel
		AND major_version_sort(version) >= major_version_sort(min_version)
where build_date(build_id) > ( current_date - 30 )
	AND version_matches_channel(releases_raw.version, releases_raw.build_type);

--fix ESR versions

UPDATE releases_recent
SET build_type = 'ESR'
WHERE build_type ILIKE 'Release'
	AND version ILIKE '%esr';

-- insert WebRT "releases", which are copies of Firefox releases
-- insert them only if the FF release is greater than the first
-- release for WebRT

INSERT INTO releases_recent
SELECT 'WebappRuntime',
	version, beta_number, build_id,
	build_type, platform,
	is_rapid, is_rapid_beta, repository
FROM releases_recent
	JOIN products
		ON products.product_name = 'WebappRuntime'
WHERE releases_recent.product_name = 'Firefox'
	AND major_version_sort(releases_recent.version)
		>= major_version_sort(products.rapid_release_version);

-- now put it in product_versions
-- first releases, aurora and nightly and non-rapid betas

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
    has_builds )
select releases_recent.product_name,
	to_major_version(version),
	version,
	version_string(version, releases_recent.beta_number),
	releases_recent.beta_number,
	version_sort(version, releases_recent.beta_number),
	build_date(min(build_id)),
	sunset_date(min(build_id), releases_recent.build_type ),
	releases_recent.build_type::citext,
	( releases_recent.build_type IN ('aurora', 'nightly') )
from releases_recent
	left outer join product_versions ON
		( releases_recent.product_name = product_versions.product_name
			AND releases_recent.version = product_versions.release_version
			AND releases_recent.beta_number IS NOT DISTINCT FROM product_versions.beta_number )
where is_rapid
    AND product_versions.product_name IS NULL
    AND NOT releases_recent.is_rapid_beta
group by releases_recent.product_name, version,
	releases_recent.beta_number,
	releases_recent.build_type::citext;

-- insert rapid betas "parent" products
-- these will have a product, but no builds

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
    has_builds )
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
    TRUE
from releases_recent
    join products ON releases_recent.product_name = products.release_name
    left outer join product_versions ON
        ( releases_recent.product_name = product_versions.product_name
            AND releases_recent.version = product_versions.release_version
            AND product_versions.beta_number = 0 )
where is_rapid
    and releases_recent.is_rapid_beta
group by products.product_name, version;

-- finally, add individual betas for rapid_betas
-- these need to get linked to their master rapid_beta

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
    rapid_beta_id )
select products.product_name,
    to_major_version(version),
    version,
    version_string(version, releases_recent.beta_number),
    releases_recent.beta_number,
    version_sort(version, releases_recent.beta_number),
    build_date(min(build_id)),
    rapid_parent.sunset_date,
    'beta',
	rapid_parent.product_version_id
from releases_recent
    join products ON releases_recent.product_name = products.release_name
    left outer join product_versions ON
        ( releases_recent.product_name = product_versions.product_name
            AND releases_recent.version = product_versions.release_version
            AND product_versions.beta_number = releases_recent.beta_number )
    join product_versions as rapid_parent ON
    	releases_recent.version = rapid_parent.release_version
    	and rapid_parent.is_rapid_beta
where is_rapid
    and releases_recent.is_rapid_beta
group by products.product_name, version, rapid_parent.product_version_id,
	releases_recent.beta_number, rapid_parent.sunset_date;

-- add build ids
-- note that rapid beta parent records will have no buildids of their own

insert into product_version_builds
select distinct product_versions.product_version_id,
		releases_recent.build_id,
		releases_recent.platform,
		releases_recent.repository
from releases_recent
	join product_versions
		ON releases_recent.product_name = product_versions.product_name
		AND releases_recent.version = product_versions.release_version
		AND releases_recent.build_type = product_versions.build_type
		AND ( releases_recent.beta_number IS NOT DISTINCT FROM product_versions.beta_number )
	left outer join product_version_builds ON
		product_versions.product_version_id = product_version_builds.product_version_id
		AND releases_recent.build_id = product_version_builds.build_id
		AND releases_recent.platform = product_version_builds.platform
where product_version_builds.product_version_id is null;

drop table releases_recent;

return true;
end; $f$;

