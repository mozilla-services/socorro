/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

-- create function for sorting old versions

create or replace function old_version_sort(
	vers text ) 
returns text
language sql
immutable 
as $f$
SELECT to_char( matched[1]::int, 'FM000' )
	|| to_char( matched[2]::int, 'FM000' )
	|| CASE WHEN matched[3] = 'b' THEN 'b'
		ELSE 'z' END
	|| '000'
	|| to_char( coalesce( matched[4]::int, 0 ), 'FM000' )
FROM ( SELECT regexp_matches($1, $x$^(\d+).*?\.(\d+)(b?)[^\.]*(?:\.(\d+))*$x$) as matched) as match 
LIMIT 1;
$f$;

BEGIN;

-- add column for new sort

ALTER TABLE productdims
ADD version_sort TEXT;

-- populate column

UPDATE productdims SET version_sort = old_version_sort(version);

-- drop old trigger

DROP TRIGGER version_sort_insert_trigger ON productdims;
DROP FUNCTION version_sort_insert_trigger();

-- add new trigger

CREATE FUNCTION version_sort_trigger ()
RETURNS trigger
LANGUAGE plpgsql
AS $f$
BEGIN
	-- on insert or update, makes sure that the
	-- version_sort column is correct
	NEW.version_sort := old_version_sort(NEW.version);
	RETURN NEW;
END;
$f$;

CREATE TRIGGER version_sort_trigger 
BEFORE INSERT OR UPDATE ON productdims 
FOR EACH ROW EXECUTE PROCEDURE version_sort_trigger();

END;
