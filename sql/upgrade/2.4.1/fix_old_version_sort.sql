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
	|| CASE WHEN matched[3] = 'b' THEN 'b'
		ELSE 'z' END
	|| '000'
	|| to_char( coalesce( matched[4]::int, 0 ), 'FM000' )
FROM ( SELECT regexp_matches($1, $x$^(\d+)[^\d]*\.(\d+)(b?)[^\.]*(?:\.(\d+))*$x$) as matched) as match 
LIMIT 1;
$f$;

UPDATE productdims SET version_sort = old_version_sort(version);

UPDATE product_visibility 
	SET end_date = CURRENT_DATE
FROM productdims
WHERE productdims.id = product_visibility.productdims_id
	AND product = 'Firefox'
	AND version IN ( '3.6.3','3.6.4pre' );
	


