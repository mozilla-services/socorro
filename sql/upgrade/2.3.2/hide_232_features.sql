
create or replace view product_selector as
select product_name, version_string, 'new'::text as which_table
from product_versions
where now() <= sunset_date
	and build_type IN ('Release','Beta')
union all
select product, version, 'old'::text as which_ui
from productdims join product_visibility
	on productdims.id = product_visibility.productdims_id
	left join product_versions on productdims.product = product_versions.product_name
		and productdims.version = product_versions.release_version
		and product_versions.build_type IN ('Release','Beta')
where product_versions.product_name is null
	and now() between product_visibility.start_date and ( product_visibility.end_date + interval '1 day')
order by product_name, version_string;


create or replace view product_info as
select product_versions.product_version_id, product_versions.product_name, version_string, 'new'::text as which_table,
	build_date as start_date, sunset_date as end_date,
	featured_version as is_featured, build_type,
	(throttle * 100)::numeric(5,2) as throttle
from product_versions
	JOIN product_release_channels
		ON product_versions.product_name = product_release_channels.product_name
		AND product_versions.build_type = product_release_channels.release_channel
where build_type IN ('Release','Beta')
union all
select productdims.id, product, version, 'old'::text,
	product_visibility.start_date, product_visibility.end_date,
	featured, release_build_type_map.build_type,
	throttle
from productdims join product_visibility
	on productdims.id = product_visibility.productdims_id
	join release_build_type_map ON
		productdims.release = release_build_type_map.release
	left join product_versions on productdims.product = product_versions.product_name
		and productdims.version = product_versions.release_version
		and product_versions.build_type IN ('Release','Beta')
where product_versions.product_name is null
order by product_name, version_string;