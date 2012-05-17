/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1


SELECT create_table_if_not_exists (
	'special_product_platforms',
	$x$
	CREATE TABLE special_product_platforms (
		platform citext not null,
		repository citext not null,
		release_channel citext not null,
		release_name citext not null,
		product_name citext not null,
		min_version major_version not null,
		constraint special_product_platforms_key 
			primary key ( release_name, platform, repository, release_channel )
	);
	
	INSERT INTO special_product_platforms
	VALUES ( 'android', 'mozilla-release', 'release', 'mobile', 'FennecAndroid', '10.0' ),
		( 'android', 'mozilla-release', 'beta', 'mobile', 'FennecAndroid', '10.0' ),
		( 'android', 'mozilla-beta', 'beta', 'mobile', 'FennecAndroid', '10.0' ),
		( 'android-arm', 'mozilla-central-android', 'nightly', 'mobile', 'FennecAndroid', '10.0' ),
		( 'android-arm', 'mozilla-central-android', 'aurora', 'mobile', 'FennecAndroid', '10.0' );
	$x$,
	'breakpad_rw' );


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
-- now covers FennecAndroid
-- now only compares releases from the last 30 days

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
	major_version_sort(version) >= major_version_sort(rapid_release_version) as is_rapid
from releases_raw
	JOIN products ON releases_raw.product_name = products.release_name
	LEFT OUTER JOIN special_product_platforms AS specials
		ON releases_raw.platform::citext = specials.platform
		AND releases_raw.product_name = specials.release_name
		AND releases_raw.repository = specials.repository
		AND releases_raw.build_type = specials.release_channel
		AND major_version_sort(version) >= major_version_sort(min_version)
where build_date(build_id) > ( current_date - 30 )
	AND version_matches_channel(releases_raw.version, releases_raw.build_type)
	AND releases_raw.repository NOT LIKE '%debug%';

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
select releases_recent.product_name,
	major_version(version),
	version,
	version_string(version, releases_recent.beta_number),
	releases_recent.beta_number,
	version_sort(version, releases_recent.beta_number),
	build_date(min(build_id)),
	sunset_date(min(build_id), releases_recent.build_type ),
	releases_recent.build_type::citext
from releases_recent
	left outer join product_versions ON
		( releases_recent.product_name = product_versions.product_name
			AND releases_recent.version = product_versions.release_version
			AND releases_recent.beta_number IS NOT DISTINCT FROM product_versions.beta_number )
where is_rapid
    AND product_versions.product_name IS NULL
group by releases_recent.product_name, version, 
	releases_recent.beta_number, 
	releases_recent.build_type::citext;

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
from releases_recent
    join products ON releases_recent.product_name = products.release_name
    left outer join product_versions ON
        ( releases_recent.product_name = product_versions.product_name
            AND releases_recent.version = product_versions.release_version
            AND product_versions.beta_number = 999 )
where is_rapid
    AND releases_recent.product_name IS NULL
    AND releases_recent.build_type ILIKE 'release'
group by products.product_name, version;

-- add build ids

insert into product_version_builds
select distinct product_versions.product_version_id,
		releases_recent.build_id,
		releases_recent.platform
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

-- add build ids for final beta

insert into product_version_builds
select distinct product_versions.product_version_id,
		releases_recent.build_id,
		releases_recent.platform
from releases_recent
	join product_versions
		ON releases_recent.product_name = product_versions.product_name
		AND releases_recent.version = product_versions.release_version
		AND releases_recent.build_type ILIKE 'release'
		AND product_versions.beta_number = 999
	left outer join product_version_builds ON
		product_versions.product_version_id = product_version_builds.product_version_id
		AND releases_recent.build_id = product_version_builds.build_id
		AND releases_recent.platform = product_version_builds.platform
where product_version_builds.product_version_id is null;

return true;
end; $f$;