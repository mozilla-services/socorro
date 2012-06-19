\set ON_ERROR_STOP 1

-- add support for rapid beta versions here

begin;

drop view if exists product_selector;

create or replace view product_selector as
select product_name, version_string, 'new'::text as which_table,
	version_sort
from product_versions
where now() <= sunset_date
order by product_name, version_string;

alter view product_selector owner to breakpad_rw;

end;

-- product_info view
-- used to power several different views of the application

begin;

drop view if exists product_info CASCADE;
DROP VIEW IF EXISTS default_versions;

create or replace view product_info as
select product_versions.product_version_id, product_versions.product_name, version_string, 'new'::text as which_table,
	build_date as start_date, sunset_date as end_date,
	featured_version as is_featured, build_type,
	(throttle * 100)::numeric(5,2) as throttle,
	version_sort, products.sort as product_sort,
	release_channels.sort as channel_sort,
    ( build_type IN ( 'Aurora', 'Nightly' ) 
      OR ( build_type = 'Beta' 
      	   AND major_version_sort(major_version) <= major_version_sort(rapid_beta_version) ) )
      AS has_builds
	from product_versions
	JOIN product_release_channels
		ON product_versions.product_name = product_release_channels.product_name
		AND product_versions.build_type = product_release_channels.release_channel
	JOIN products ON product_versions.product_name = products.product_name
	JOIN release_channels ON product_versions.build_type = release_channels.release_channel
order by product_name, version_string;

alter view product_info owner to breakpad_rw;

CREATE OR REPLACE VIEW default_versions
as
SELECT product_name, version_string, product_version_id FROM (
SELECT product_name, version_string, product_version_id,
	row_number() over ( PARTITION BY product_name 
		ORDER BY ( current_date BETWEEN start_date and end_date ) DESC,
		is_featured DESC, 
		channel_sort DESC ) as sort_count
FROM product_info ) as count_versions
WHERE sort_count = 1;

ALTER VIEW default_versions OWNER TO breakpad_rw;

CREATE OR REPLACE VIEW default_versions_builds
as
SELECT product_name, version_string, product_version_id FROM (
SELECT product_name, version_string, product_version_id,
    row_number() over ( PARTITION BY product_name 
        ORDER BY ( current_date BETWEEN start_date and end_date ) DESC,
        is_featured DESC, 
        channel_sort DESC ) as sort_count
FROM product_info 
WHERE has_builds ) as count_versions
WHERE sort_count = 1;

ALTER VIEW default_versions OWNER TO breakpad_rw;

END;


