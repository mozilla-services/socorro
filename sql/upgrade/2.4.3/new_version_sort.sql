/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

create or replace function old_version_sort(
	vers text ) 
returns text
language sql
immutable 
as $f$
SELECT to_char( matched[1]::int, 'FM000' )
	|| to_char( matched[2]::int, 'FM000' )
	|| to_char( coalesce( matched[4]::int, 0 ), 'FM000' )
	|| CASE WHEN matched[3] <> '' THEN 'b'
		WHEN matched[5] <> '' THEN 'b'
		ELSE 'z' END
	|| '000'
FROM ( SELECT regexp_matches($1,
$x$^(\d+)[^\d]*\.(\d+)([a-z]?)[^\.]*(?:\.(\d+))?([a-z]?).*$$x$) as matched) as match 
LIMIT 1;
$f$;

BEGIN;

drop function if exists version_number_elements(
	version_string text );

drop function if exists version_number_elements(
	version text,  beta_number int );
	
drop function if exists version_number_elements(
	version text,  beta_number int, channel text );

drop function if exists version_sort(
	version_string text );

drop function if exists version_sort(
	version text,  beta_number int );
	
drop function if exists version_sort(
	version text,  beta_number int, channel text );

create or replace function version_sort(
	version text, 
	beta_no int default 0, 
	channel citext default ''
) returns text
language plpgsql
immutable
as $f$
DECLARE vne TEXT[];
	sortstring TEXT;
	dex INT;
BEGIN

	-- regexp the version number into tokens
	vne := regexp_matches( version, $x$^(\d+)\.(\d+)([a-zA-Z]?)(\d*)(?:\.(\d+))?(?:([a-zA-Z])(\d+))?.*$$x$ );
	
	-- bump betas after the 3rd digit back
	vne[3] := coalesce(nullif(vne[3],''),vne[6]);
	vne[4] := coalesce(nullif(vne[4],''),vne[7]);

	-- handle betal numbers
	IF beta_no > 0 THEN
		vne[3] := 'b';
		vne[4] := beta_no::TEXT;
	END IF;
	
	--handle final betas
	IF version LIKE '%(beta)%' THEN
		vne[3] := 'b';
		vne[4] := '99';
	END IF;
	
	--handle release channels
	CASE channel
		WHEN 'nightly' THEN
			vne[3] := 'a';
			vne[4] := '1';
		WHEN 'aurora' THEN
			vne[3] := 'a';
			vne[4] := '2';
		WHEN 'beta' THEN
			vne[3] := 'b';
			vne[4] := COALESCE(nullif(vne[4],''),99);
		WHEN 'release' THEN
			vne[3] := '';
			vne[4] := '';
		ELSE
			NULL;
	END CASE;
	
	--assemble string
	sortstring := version_sort_digit(vne[1]) 
		|| version_sort_digit(vne[2]) 
		|| version_sort_digit(vne[5]) 
		|| COALESCE(vne[3],'z')
		|| version_sort_digit(vne[4]) ;
		
	RETURN sortstring;
END;$f$;	
	
COMMIT;
	
	
SELECT regexp_matches(
'2.1', $x$^(\d+)[^\d]*\.(\d+)([a-z]?)[^\.]*(?:\.(\d+))?([a-z]?).*$$x$);