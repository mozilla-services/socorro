\SET ON_ERROR_STOP 1

BEGIN;

-- new domain major_version just checks that we don't have
-- garbage in this field

create domain major_version AS text
	CHECK ( VALUE ~ $x$^\d+\.\d+$x$ );
	
alter domain major_version owner to breakpad_rw;

-- new products table.  just lists each top-level product
-- release_name matches the FTP server
-- rapid_release_version is the first major version 
-- we will include in the new tcbs, etc.
-- data is manually updated

create table products (
    product_name citext not null primary key,
    sort int2 not null default 0,
    rapid_release_version major_version,
    release_name citext not null
);

alter table products owner to breakpad_rw;
     
-- release channel listing, just for checking data and sorting     
-- data is manually added
     
create table release_channels (
    release_channel citext not null primary key,
    sort int2 not null default 0 );

alter table release_channels owner to breakpad_rw;
    
-- dimension table including all released products and versions
-- data comes from the FTP site via releases_raw
-- replaces "productdims"
-- version_string is the full version, i.e. 6.0b5
-- release_version should match what we get in reports
-- version_sort allows sorting by version
-- build_date and sunset_date determine visibility, and replace
-- the product_visibility table

create table product_versions (
    product_version_id SERIAL not null primary key,
    product_name citext not null references products(product_name),
    major_version major_version not null,
    release_version citext not null,
    version_string citext not null,
    beta_number int,
    version_sort text not null default 0,
    build_date date not null, -- UTC date
    sunset_date date not null, -- UTC date
    featured_version boolean not null default false,
    build_type citext not null default 'release',
    constraint product_version_version_key unique (product_name, version_string)
);

alter table product_versions owner to breakpad_rw;

create unique index product_version_unique_beta 
	on product_versions(product_name, major_version,beta_number) 
	where beta_number IS NOT NULL;
create index product_versions_product_name on product_versions(product_name);
create index product_versions_major_version on product_versions(major_version);
create index product_versions_version_sort on product_versions(version_sort);

-- buildids per product, again from releases_raw
-- here in order to match betas up

create table product_version_builds (
	product_version_id INT not null references product_versions(product_version_id),
	build_id NUMERIC NOT NULL,
	platform text,
	constraint product_version_builds_key primary key (product_version_id, build_id, platform)
);

alter table product_version_builds owner to breakpad_rw;

-- view for choosing whether to use the old TCBS or the new one
-- lists all "current" products

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
where product_versions.product_name is null 
	and now() between product_visibility.start_date and ( product_visibility.end_date + interval '1 day')
order by product_name, version_string;

alter view product_selector owner to breakpad_rw;

-- mapping table to map old release types to new build types

create table release_build_type_map (
	release release_enum not null primary key,
	build_type citext not null
);

alter table release_build_type_map owner to breakpad_rw;

-- product_info view
-- used to power several different views of the application

create or replace view product_info as
select product_name, version_string, 'new'::text as which_table,
	build_date as start_date, sunset_date as end_date, 
	featured_version as is_featured, build_type
from product_versions
where build_type IN ('Release','Beta')
union all
select product, version, 'old'::text,
	product_visibility.start_date, product_visibility.end_date,
	featured, release_build_type_map.build_type
from productdims join product_visibility
	on productdims.id = product_visibility.productdims_id
	join release_build_type_map ON 
		productdims.release = release_build_type_map.release
	left join product_versions on productdims.product = product_versions.product_name
		and productdims.version = product_versions.release_version
where product_versions.product_name is null
order by product_name, version_string;

-- need to alter signatures update procedure to update signatures instead of signature_first

-- signatures dimension table
-- lists each signature and assigns a surrogate key
-- data automatically updated by daily batch
-- note that first_report and first_build will be wonky until
-- after we've been on the new releases for a while
-- for this table, NULL signature and empty string are combined

create table signatures (
    signature_id SERIAL not null primary key,
    signature text unique,
    first_report  timestamp without time zone,
    first_build numeric
);

alter table signatures owner to breakpad_rw;

-- new TCBS matview. used for all "new" products
-- generally joined with product_versions and signature_product_rollup
-- updated by daily batch, per UTC day

create table tcbs (
    signature_id int not null references signatures(signature_id),
    report_date date not null,
    product_version_id int not null references product_versions(product_version_id),
    process_type citext not null,
    release_channel citext not null references release_channels(release_channel),
    report_count int not null default 0,
    win_count int not null default 0,
    mac_count int not null default 0,
    lin_count int not null default 0,
    constraint tcbs_key primary key (signature_id, report_date, product_version_id, process_type, release_channel) 
);

create index tcbs_signature on tcbs(signature_id);
create index tcbs_report_date on tcbs(report_date);
create index tcbs_product_version on tcbs(product_version_id, report_date);

alter table tcbs owner to breakpad_rw;

-- matview listing signatures by product for new products only
-- updated by daily batch

create table signature_products (
	signature_id INT NOT NULL references signatures(signature_id),
	product_version_id int not null references product_versions(product_version_id),
	first_report timestamp,
	constraint signature_products_key primary key (signature_id, product_version_id)
);

create index signature_products_product_version on signature_products(product_version_id);

alter table signature_products owner to breakpad_rw;

-- rollup of signature_products
-- used for main TCBS screen
-- updated by daily batch

create table signature_products_rollup (
	signature_id INT NOT NULL references signatures(signature_id) primary key,
	ver_count INT NOT NULL default 0,
	version_list TEXT[] not null default '{}'
);

alter table signature_products_rollup owner to breakpad_rw;

-- intersection of products and release channels
-- used mainly to track throttling information
-- updated manually

create table product_release_channels (
	product_name citext not null references products(product_name),
	release_channel citext not null references release_channels(release_channel),
	throttle numeric not null default 1.0,
	constraint product_release_channels_key primary key (product_name, release_channel)
);

alter table product_release_channels owner to breakpad_rw;

-- matching table to match the strings we receive with 
-- actual release channels
-- update manually

create table release_channel_matches (
	release_channel citext not null references release_channels(release_channel),
	match_string text not null,
	constraint release_channel_matches_key primary key (release_channel, match_string)
);

alter table release_channel_matches owner to breakpad_rw;

-- lookup list with the list of canonical operating system names
-- updated manually

create table os_names (
	os_name citext not null primary key
);

alter table os_names owner to breakpad_rw;

-- dimension with a list of all oses and "versions"
-- in this case, version is the first two digits of whatever
-- appears in the version string (e.g. Mac OSX 10.4, Windows 6.1)
-- updated by daily batch
-- contains many garbage values

create table os_versions (
	os_version_id SERIAL NOT NULL primary key,
	os_name citext not null references os_names(os_name),
	major_version int not null,
	minor_version int not null,
	constraint os_versions_key unique (os_name, major_version, minor_version)
);

alter table os_versions owner to breakpad_rw;

-- matching table for matching the strings we receive 
-- with the list of OS names.  
-- updated manually

create table os_name_matches (
		os_name citext not null references os_names(os_name),
		match_string text not null,
		constraint os_name_matches_key primary key ( os_name, match_string )
);

alter table os_name_matches owner to breakpad_rw;

-- Average Daily Users table which contains cleaned 
-- and summarized data from raw_adu
-- updated once per day by batch job

create table product_adu (
	product_version_id int not null references product_versions(product_version_id),
	adu_date date not null,
	adu_count int not null default 0,
	constraint product_adu_key primary key (product_version_id, adu_date)
);

alter table product_adu owner to breakpad_rw;


commit;
