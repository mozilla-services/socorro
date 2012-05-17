/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

create or replace function sunset_date (
	build_id numeric, build_type citext )
returns date
language sql immutable as $f$
-- sets a sunset date for visibility
-- based on a build number
-- current spec is 18 weeks for releases
-- 9 weeks for everything else
select ( build_date($1) +
	case when $2 = 'release'
		then interval '18 weeks'
	when $2 = 'ESR'
		then interval '18 weeks'
	else
		interval '9 weeks'
	end ) :: date
$f$;


--- fix to account for esr
create or replace function version_matches_channel (
	version text, channel citext )
returns boolean
language sql
immutable strict
as $f$
SELECT CASE WHEN $1 ILIKE '%a1' AND $2 ILIKE 'nightly%'
	THEN TRUE
WHEN $1 ILIKE '%a2' AND $2 = 'aurora' 
	THEN TRUE
WHEN $1 ILIKE '%esr' AND $2 IN ( 'release', 'esr' )
	THEN TRUE
WHEN $1 NOT ILIKE '%a%' AND $1 NOT ILIKE '%esr' AND $2 IN ( 'beta', 'release' )
	THEN TRUE
ELSE FALSE END;
$f$;