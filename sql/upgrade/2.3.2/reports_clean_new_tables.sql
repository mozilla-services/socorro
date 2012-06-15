\set ON_ERROR_STOP 1

SELECT create_table_if_not_exists ( 'reasons', $x$	
create table reasons (
  reason_id serial not null primary key,
  reason citext not null unique,
  first_seen timestamptz
);

insert into reasons ( reason, first_seen ) values ( '', '2011-01-01' );
$x$, 'breakpad_rw');

SELECT create_table_if_not_exists ( 'flash_versions', $x$	
create table flash_versions (
  flash_version_id serial not null primary key,
  flash_version citext not null unique,
  first_seen timestamptz
);

insert into flash_versions ( flash_version, first_seen ) values ( '', '2011-01-01' );
$x$, 'breakpad_rw');

SELECT create_table_if_not_exists ( 'addresses', $x$	
create table addresses ( 
  address_id serial not null primary key,
  address citext not null unique,
  first_seen timestamptz
);

insert into addresses ( address, first_seen ) values ( '', '2011-01-01' );
$x$, 'breakpad_rw');

SELECT create_table_if_not_exists ( 'domains', $x$	
create table domains (
	domain_id serial not null primary key,
	domain citext not null unique,
	first_seen timestamptz
);

insert into domains ( domain, first_seen ) values ( '', '2011-01-01' );
$x$, 'breakpad_rw');

SELECT create_table_if_not_exists ( 'process_types', $x$
create table process_types (
	process_type citext not null primary key
);

insert into process_types 
values ( 'browser' ), ( 'plugin' ),  ( 'content' );
$x$, 'breakpad_rw');

SELECT create_table_if_not_exists ( 'reports_clean', $x$	
create table reports_clean (
  uuid text not null primary key,
  date_processed timestamptz not null,
  client_crash_date timestamptz,
  product_version_id int not null,
  build numeric,
  signature_id int not null,
  install_age interval,
  uptime interval,
  reason_id int not null, 
  address_id int not null,
  os_name citext not null,
  os_version_id int not null,
  hang_id text,
  flash_version_id int not null,
  process_type citext not null,
  release_channel citext not null,
  duplicate_of text,
  domain_id int not null
);
$x$, 'breakpad_rw');

SELECT create_table_if_not_exists ( 'reports_user_info', $x$	
create table reports_user_info (
  uuid text not null primary key,
  date_processed timestamptz not null, 
  user_comments citext,
  app_notes citext,
  email citext,
  url text
);
$x$, 'breakpad_rw');

SELECT create_table_if_not_exists ( 'reports_bad', $x$	
create table reports_bad (
	uuid text not null,
	date_processed timestamptz not null
);
$x$, 'breakpad_rw');
	
	