\set ON_ERROR_STOP 1

create or replace function ts2pacific(
  timestamp )
returns timestamptz 
language sql
stable strict as $f$
SELECT $1 AT TIME ZONE 'America/Los_Angeles';
$f$;

create or replace function pacific2ts (
	timestamptz )
returns timestamp
language sql
stable strict 
set timezone = 'America/Los_Angeles' 
as $f$
SELECT $1::timestamp;
$f$;

create or replace function week_begins_utc (
	timestamp )
returns timestamptz 
language sql 
stable strict
SET TIMEZONE = 'UTC' as
$f$
SELECT date_trunc('week', ts2pacific($1));
$f$;	

create or replace function week_begins_utc (
	timestamptz )
returns timestamptz 
language sql 
stable strict
SET TIMEZONE = 'UTC' as
$f$
SELECT date_trunc('week', $1);
$f$;	

create or replace function tz2pac_ts(
	timestamptz )
returns timestamp
language sql
stable strict as
$f$
SELECT $1 AT TIME ZONE 'America/Los_Angeles';
$f$;
	
create or replace function url2domain (
	some_url text )
returns citext
language sql
immutable strict 
as $f$
select substring($1 FROM $x$^([\w:]+:/+(?:\w+\.)*\w+).*$x$)::citext
$f$;

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
  product_version_id int,
  build numeric,
  signature_id int,
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
	
	