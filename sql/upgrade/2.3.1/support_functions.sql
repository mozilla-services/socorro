/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

create or replace function ts2pacific(
  timestamp )
returns timestamptz 
language sql
stable as $f$
SELECT $1 AT TIME ZONE 'America/Los_Angeles';
$f$;

create or replace function pacific2ts (
	timestamptz )
returns timestamp
language sql
stable
set timezone = 'America/Los_Angeles' 
as $f$
SELECT $1::timestamp;
$f$;

create or replace function week_begins_utc (
	timestamp )
returns timestamptz 
language sql 
stable
SET TIMEZONE = 'UTC' as
$f$
SELECT date_trunc('week', ts2pacific($1));
$f$;	

create or replace function week_begins_utc (
	timestamptz )
returns timestamptz 
language sql 
stable
SET TIMEZONE = 'UTC' as
$f$
SELECT date_trunc('week', $1);
$f$;	

create or replace function tz2pac_ts(
	timestamptz )
returns timestamp
language sql
stable as
$f$
SELECT $1 AT TIME ZONE 'America/Los_Angeles';
$f$;
	
create or replace function url2domain (
	some_url text )
returns citext
language sql
immutable
as $f$
select substring($1 FROM $x$^([\w:]+:/+(?:\w+\.)*\w+).*$x$)::citext
$f$;

create or replace function utc_day_is (
	timestamptz, timestamp )
returns boolean
language sql
immutable as
$f$
select $1 >= ( $2 AT TIME ZONE 'UTC' )
	AND $1 < ( $2 AT TIME ZONE 'UTC' + INTERVAL '1 day' );
$f$;
	
create or replace function utc_day_near (
	timestamptz, timestamp )
returns boolean
language sql
immutable as
$f$
select $1 > ( $2 AT TIME ZONE 'UTC' - INTERVAL '1 day' )
	AND $1 < ( $2 AT TIME ZONE 'UTC' + INTERVAL '2 days' )
$f$;
	
