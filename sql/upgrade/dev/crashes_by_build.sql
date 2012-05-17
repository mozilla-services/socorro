/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\SET ON_ERROR_STOP ON

create or replace function utctz2date (
	timestamptz )
returns date
language sql
stable
set timezone = 'UTC'
as
$f$
SELECT $1::DATE;
$f$;

SELECT create_table_if_not_exists( 'crashes_by_build', $x$
create table crashes_by_build (
	product_version_id int not null references product_versions(product_version_id) on delete cascade,
	build_id numeric not null,
	build_date date not null,
	report_date date not null,
	crash_count int not null default 0,
	constraint crashes_by_build_key 
		primary key ( product_version_id, build_id, report_date )
);$x$, 'breakpad_rw', 
	ARRAY [ 'report_date', 'build_date' ] );
	
SET work_mem = '512MB';
	
INSERT INTO crashes_by_build
SELECT reports_clean.product_version_id, reports_clean.build, 	
	build_date(reports_clean.build),
	utctz2date(date_processed), count(*)
FROM reports_clean
	JOIN product_versions USING ( product_version_id )
	JOIN product_version_builds ON reports_clean.product_version_id =
		product_version_builds.product_version_id
		AND reports_clean.build = product_version_builds.build_id
WHERE date_processed BETWEEN '2011-11-09' AND '2011-11-16'
GROUP BY reports_clean.product_version_id, reports_clean.build, 
	build_date(build), utctz2date(date_processed);
	