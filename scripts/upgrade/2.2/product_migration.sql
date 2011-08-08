\SET ON_ERROR_STOP 1

BEGIN;

-- populate all the new product and release channel data

insert into products ( product_name, sort, rapid_release_version, release_name)
values ( 'Firefox', 1, '5.0', 'firefox' ),
	( 'Thunderbird', 2, NULL, 'thunderbird' ),
	( 'Fennec', 3, '5.0', 'mobile' ),
	( 'Camino', 4, NULL, 'camino' ),
	( 'Seamonkey', 5, NULL, 'seamonkey' );
	
insert into release_channels ( release_channel, sort )
values ( 'Nightly', 1 ),
	( 'Aurora', 2 ),
	( 'Beta', 3 ),
	( 'Release', 4 );
	
-- add product_release_channels as a cartesian join	

insert into product_release_channels ( product_name, release_channel )
select product_name, release_channel
from products, release_channels;

-- throttling firefox releases by 90%

update product_release_channels
set throttle = 0.1
where product_name = 'Firefox'
	and release_channel = 'Release';
	
-- match strings for fuzzy matching of channel names

insert into release_channel_matches ( release_channel, match_string )
values ( 'Release', 'release' ),
	( 'Release', 'default' ),
	( 'Beta', 'beta' ),
	( 'Aurora', 'aurora' ),
	( 'Nightly', 'nightly%' );
	
insert into release_build_type_map ( release, build_type )
values ( 'major', 'Release' ),
	( 'development', 'Beta' ),
	( 'milestone', 'Aurora' );

-- populate product_versions

insert into product_versions (
    product_name,
    major_version,
    release_version,
    version_string,
    beta_number,
    version_sort,
    build_date,
    sunset_date,
    build_type )
select products.product_name, 
	major_version(version),
	version,
	version_string(version, beta_number),
	beta_number,
	version_sort(version, beta_number),
	build_date(min(build_id)),
	sunset_date(min(build_id), build_type ),
	build_type
from releases_raw
	join products ON products.release_name = releases_raw.product_name
where major_version_sort(version) >= major_version_sort(rapid_release_version)
group by products.product_name, version, beta_number, build_type;

insert into product_version_builds
	select product_version_id,
		build_id,
		platform
from releases_raw
	join product_versions
		ON releases_raw.product_name = product_versions.product_name
		AND releases_raw.version = product_versions.release_version
		AND releases_raw.beta_number IS NOT DISTINCT FROM product_versions.beta_number;
		
analyze products;
analyze release_channels;
analyze product_versions;
analyze product_version_builds;
analyze product_release_channels;
analyze release_channel_matches;

-- copy featured versions

update product_versions set featured_version = true
from productdims join product_visibility
  on productdims.id = product_visibility.productdims_id
where product_versions.product_name = productdims.product
  and product_versions.version_string = productdims.version
  and product_visibility.featured;
		
COMMIT;
		
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
-- currently we are only adding releases and betas

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
	version_string(version, releases_raw.beta_number),
	releases_raw.beta_number,
	version_sort(version, releases_raw.beta_number),
	build_date(min(build_id)),
	sunset_date(min(build_id), releases_raw.build_type ), 
	releases_raw.build_type
from releases_raw
	join products ON releases_raw.product_name = products.release_name
	left outer join product_versions ON 
		( releases_raw.product_name = products.release_name
			AND releases_raw.version = product_versions.release_version
			AND releases_raw.beta_number IS NOT DISTINCT FROM product_versions.beta_number )
where major_version_sort(version) >= major_version_sort(rapid_release_version)
	AND product_versions.product_name IS NULL
	AND releases_raw.build_type IN ('release','beta')
group by products.product_name, version, releases_raw.beta_number, releases_raw.build_type;

insert into product_version_builds
	select product_versions.product_version_id,
		releases_raw.build_id,
		releases_raw.platform
from releases_raw
	join product_versions
		ON releases_raw.product_name = product_versions.product_name
		AND releases_raw.version = product_versions.release_version
		AND releases_raw.beta_number IS NOT DISTINCT FROM product_versions.beta_number
	left outer join product_version_builds ON
		product_versions.product_version_id = product_version_builds.product_version_id
		AND releases_raw.build_id = product_version_builds.build_id
where product_version_builds.product_version_id is null;

return true;
end; $f$;