/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

create or replace function reports_clean_done(
	updateday date )
returns boolean
language plpgsql
as $f$
-- this function checks that reports_clean has been updated
-- all the way to the last hour of the UTC day
BEGIN

PERFORM 1 
	FROM reports_clean
	WHERE date_processed BETWEEN ( ( updateday::timestamp at time zone 'utc' ) + interval '23 hours' )
		AND ( ( updateday::timestamp at time zone 'utc' ) + interval '1 day' )
	LIMIT 1;
IF FOUND THEN
	RETURN TRUE;
ELSE
	RETURN FALSE;
END IF;
END; $f$;


create or replace function tstz_between(
	tstz timestamp with time zone, bdate date, fdate date)
returns boolean
language sql
immutable
as $f$
SELECT $1 BETWEEN ( $2::timestamp AT TIME ZONE 'UTC' ) 
	AND ( $3::timestamp AT TIME ZONE 'UTC' + INTERVAL '1 day' );
$f$;

