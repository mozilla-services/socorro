\set ON_ERROR_STOP 1

insert into releases_raw (
	product_name, version, platform, build_id, build_type, beta_number, repository )
select distinct product_name, version, 'android', build_id, build_type, beta_number, repository
from releases_raw
where product_name = 'mobile' and version = '9.0' and build_type IN ( 'release', 'beta' );

insert into releases_raw (
	product_name, version, platform, build_id, build_type, beta_number, repository )
select distinct product_name, version, 'android-arm', build_id, build_type, beta_number, 'mozilla-central-android'
from releases_raw
where product_name = 'mobile' and version like '9.0%' and build_type IN ( 'aurora', 'nightly' );

update releases_raw 
set repository = 'mozilla-central-android' 
where repository = 'birch-android'
	and product_name = 'mobile'
	and  ( version LIKE '11%'
		or version like '10%' );

select update_product_versions();

insert into raw_adu ( adu_count, date, product_name, product_os_platform,
	product_os_version, product_version, build, build_channel, product_guid )
select adu_count, date, raw_adu.product_name, product_os_platform,
	product_os_version, product_version, build, build_channel, productid
from raw_adu, product_productid_map as map
where map.rewrite
	and map.product_name = 'FennecAndroid'
	and raw_adu.product_name = 'Fennec'
	and raw_adu.product_os_platform = 'Linux'
	and ( raw_adu.product_version LIKE '9.0%' 
		or raw_adu.product_version LIKE '10.0%'
		or raw_adu.product_version LIKE '11.0%' );


DO $f$
DECLARE thisdate DATE;
BEGIN
 
	thisdate := '2011-12-07';
	
	WHILE thisdate < '2011-12-13' LOOP
	
		raise info 'backfilling %', thisdate;
		
		PERFORM backfill_adu(thisdate);
		
		thisdate := thisdate + 1;
		
	END LOOP;
	
END;$f$;
	

UPDATE reports
SET product = 'FennecAndroid'
WHERE product = 'Fennec'
	AND os_name ILIKE 'linux%'
	AND date_processed > '2011-12-07'
	AND ( version LIKE '9.0%' or version like '10.0%' or version like '11.0%' )
	AND random() > 0.5;
	
SELECT backfill_matviews('2011-12-10','','2011-12-12');

update product_versions set featured_version = true where product_name = 'FennecAndroid' and version_string in ('11.0a1','9.0b5','9.0b6','10.0a2');



