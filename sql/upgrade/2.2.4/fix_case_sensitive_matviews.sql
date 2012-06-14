/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

DROP FUNCTION update_signatures(DATE);

CREATE OR REPLACE FUNCTION update_signatures (
	updateday DATE, checkdata BOOLEAN DEFAULT TRUE )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
AS $f$
BEGIN

-- new function for updating signature information post-rapid-release
-- designed to be run once per UTC day.
-- running it repeatedly won't cause issues
-- combines NULL and empty signatures

-- create temporary table

create temporary table new_signatures
on commit drop as
select coalesce(signature,'') as signature, 
	product::citext as product, 
	version::citext as version, 
	build, NULL::INT as product_version_id,
	min(date_processed) as first_report
from reports
where date_processed >= utc_day_begins_pacific(updateday)
	and date_processed <= utc_day_begins_pacific((updateday + 1))
group by signature, product, version, build;

PERFORM 1 FROM new_signatures;
IF NOT FOUND THEN
	IF checkdata THEN
		RAISE EXCEPTION 'no signature data found in reports for date %',updateday;
	END IF;
END IF;

analyze new_signatures;

-- add product IDs
update new_signatures
set product_version_id = product_versions.product_version_id
from product_versions JOIN product_version_builds
	ON product_versions.product_version_id = product_version_builds.product_version_id
where product_versions.release_version = new_signatures.version
	and product_versions.product_name = new_signatures.product
	and product_version_builds.build_id::text = new_signatures.build;

-- add product IDs for builds that don't match
update new_signatures
set product_version_id = product_versions.product_version_id
from product_versions JOIN product_version_builds
	ON product_versions.product_version_id = product_version_builds.product_version_id
where product_versions.release_version = new_signatures.version
	and product_versions.product_name = new_signatures.product
	and product_versions.build_type = 'release'
	and new_signatures.product_version_id IS NULL;

analyze new_signatures;

-- update signatures table

insert into signatures ( signature, first_report, first_build )
select new_signatures.signature, min(new_signatures.first_report),
	min(build_numeric(new_signatures.build))
from new_signatures
left outer join signatures
	on new_signatures.signature = signatures.signature
where signatures.signature is null
	and new_signatures.product_version_id is not null
group by new_signatures.signature;

-- update signature_products table

insert into signature_products ( signature_id, product_version_id, first_report )
select signatures.signature_id,
		new_signatures.product_version_id,
		min(new_signatures.first_report)
from new_signatures JOIN signatures
	ON new_signatures.signature = signatures.signature
	left outer join signature_products
		on signatures.signature_id = signature_products.signature_id
		and new_signatures.product_version_id = signature_products.product_version_id
where new_signatures.product_version_id is not null
	and signature_products.signature_id is null
group by signatures.signature_id,
		new_signatures.product_version_id;

-- recreate the rollup from scratch

DELETE FROM signature_products_rollup;

insert into signature_products_rollup ( signature_id, product_name, ver_count, version_list )
select
	signature_id, product_name, count(*) as ver_count,
		array_accum(version_string ORDER BY product_versions.version_sort)
from signature_products JOIN product_versions
	USING (product_version_id)
group by signature_id, product_name;

analyze signature_products_rollup;

-- recreate signature_bugs from scratch

DELETE FROM signature_bugs_rollup;

INSERT INTO signature_bugs_rollup (signature_id, bug_count, bug_list)
SELECT signature_id, count(*), array_accum(bug_id)
FROM signatures JOIN bug_associations USING (signature)
GROUP BY signature_id;

analyze signature_bugs_rollup;

return true;
end;
$f$;


CREATE OR REPLACE FUNCTION update_adu (
	updateday date )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
AS $f$
BEGIN
-- daily batch update procedure to update the
-- adu-product matview, used to power graphs
-- gets its data from raw_adu, which is populated
-- daily by metrics

-- check if raw_adu has been updated.  otherwise, abort.
PERFORM 1 FROM raw_adu
WHERE "date" = updateday
LIMIT 1;

IF NOT FOUND THEN
	RAISE EXCEPTION 'raw_adu not updated for %',updateday;
END IF;

-- check if ADU has already been run for the date

PERFORM 1 FROM product_adu
WHERE adu_date = updateday LIMIT 1;

IF FOUND THEN
	RAISE EXCEPTION 'update_adu has already been run for %', updateday;
END IF;

-- insert releases

INSERT INTO product_adu ( product_version_id, os_name,
		adu_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
	updateday,
	coalesce(sum(raw_adu.adu_count), 0)
FROM product_versions
	LEFT OUTER JOIN raw_adu
		ON product_versions.product_name = raw_adu.product_name::citext
		AND product_versions.version_string = raw_adu.product_version::citext
		AND product_versions.build_type ILIKE raw_adu.build_channel
		AND raw_adu.date = updateday
	LEFT OUTER JOIN os_name_matches
    	ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type = 'release'
GROUP BY product_version_id, os;

-- insert betas
-- does not include any missing beta counts; should resolve that later

INSERT INTO product_adu ( product_version_id, os_name,
        adu_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
    updateday,
    coalesce(sum(raw_adu.adu_count), 0)
FROM product_versions
    JOIN raw_adu
        ON product_versions.product_name = raw_adu.product_name::citext
        AND product_versions.release_version = raw_adu.product_version::citext
        AND raw_adu.date = updateday
    JOIN os_name_matches
    	ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type = 'Beta'
        AND raw_adu.build_channel = 'beta'
        AND EXISTS ( SELECT 1
            FROM product_version_builds
            WHERE product_versions.product_version_id = product_version_builds.product_version_id
              AND product_version_builds.build_id = build_numeric(raw_adu.build)
            )
GROUP BY product_version_id, os;

-- insert old products

INSERT INTO product_adu ( product_version_id, os_name,
        adu_date, adu_count )
SELECT productdims_id, coalesce(os_name,'Unknown') as os,
	updateday, coalesce(sum(raw_adu.adu_count),0)
FROM productdims
	JOIN product_visibility ON productdims.id = product_visibility.productdims_id
	LEFT OUTER JOIN raw_adu
		ON productdims.product = raw_adu.product_name::citext
		AND productdims.version = raw_adu.product_version::citext
		AND raw_adu.date = updateday
    LEFT OUTER JOIN os_name_matches
    	ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
WHERE updateday BETWEEN ( start_date - interval '1 day' )
	AND ( end_date + interval '1 day' )
GROUP BY productdims_id, os;

RETURN TRUE;
END; $f$;


CREATE OR REPLACE FUNCTION update_daily_crashes (
	updateday date )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
AS $f$
BEGIN
-- update the old daily crashes  yes, this is horrible
-- stuff, but until we overhaul the home page graph
-- we will continue to use it

-- apologies for badly written SQL, didn't want to rewrite it all from scratch

-- note: we are currently excluding crashes which are missing an OS_Name from the count

-- check if there are crashes for that day

PERFORM 1 FROM reports
WHERE	date_processed >= utc_day_begins_pacific(updateday)
		AND date_processed < utc_day_ends_pacific(updateday)
LIMIT 1;
IF NOT FOUND THEN 
	RAISE EXCEPTION 'No crash reports found for date %',updateday;
END IF;

-- check if daily_crashes has already been run for that day
PERFORM 1 FROM daily_crashes
WHERE adu_day = updateday
LIMIT 1;
IF FOUND THEN
	RAISE EXCEPTION 'Daily crashes appears to have already been run for %.  If you want to run it again, please use backfill_daily_crashes().',updateday;
END IF;
	
-- insert old browser crashes
-- for most crashes
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT COUNT(*) as count, daily_crash_code(process_type, hangid) as crash_code, p.id,
	substring(r.os_name, 1, 3) AS os_short_name,
	updateday
FROM product_visibility cfg
JOIN productdims p on cfg.productdims_id = p.id
JOIN reports r on p.product = r.product AND p.version = r.version
WHERE NOT cfg.ignore AND
	date_processed >= utc_day_begins_pacific(updateday)
		AND date_processed < utc_day_ends_pacific(updateday)
	AND updateday BETWEEN cfg.start_date and cfg.end_date
    AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
GROUP BY p.id, crash_code, os_short_name;

 -- insert HANGS_NORMALIZED from old data
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT count(subr.hangid) as count, 'H', subr.prod_id, subr.os_short_name,
	 updateday
FROM (
		   SELECT distinct hangid, p.id AS prod_id, substring(r.os_name, 1, 3) AS os_short_name
		   FROM product_visibility cfg
		   JOIN productdims p on cfg.productdims_id = p.id
		   JOIN reports r on p.product = r.product AND p.version = r.version
		   WHERE NOT cfg.ignore AND
				date_processed >= utc_day_begins_pacific(updateday)
					AND date_processed < utc_day_ends_pacific(updateday)
				AND updateday BETWEEN cfg.start_date and cfg.end_date
				AND hangid IS NOT NULL
                AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
		 ) AS subr
GROUP BY subr.prod_id, subr.os_short_name;

-- insert crash counts for new products
-- non-beta
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT COUNT(*) as count, daily_crash_code(process_type, hangid) as crash_code,
	product_versions.product_version_id,
	substring(os_name, 1, 3) AS os_short_name,
	updateday
FROM product_versions
JOIN reports on product_versions.product_name = reports.product::citext
	AND product_versions.version_string = reports.version::citext
WHERE
	date_processed >= utc_day_begins_pacific(updateday)
		AND date_processed < utc_day_ends_pacific(updateday)
    AND ( lower(release_channel) NOT IN ( 'nightly', 'beta', 'aurora' )
        OR release_channel IS NULL )
	AND updateday BETWEEN product_versions.build_date and sunset_date
    AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
AND product_versions.build_type <> 'beta'
GROUP BY product_version_id, crash_code, os_short_name;

-- insert crash counts for new products
-- betas
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT COUNT(*) as count, daily_crash_code(process_type, hangid) as crash_code,
	product_versions.product_version_id,
	substring(os_name, 1, 3) AS os_short_name,
	updateday
FROM product_versions
JOIN reports on product_versions.product_name = reports.product::citext
	AND product_versions.release_version = reports.version::citext
WHERE date_processed >= utc_day_begins_pacific(updateday)
		AND date_processed < utc_day_ends_pacific(updateday)
    AND release_channel ILIKE 'beta'
	AND updateday BETWEEN product_versions.build_date and sunset_date
    AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
    AND EXISTS (SELECT 1
        FROM product_version_builds
        WHERE product_versions.product_version_id = product_version_builds.product_version_id
          AND product_version_builds.build_id = build_numeric(reports.build) )
AND product_versions.build_type = 'beta'
GROUP BY product_version_id, crash_code, os_short_name;

-- insert normalized hangs for new products
-- non-beta
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT count(subr.hangid) as count, 'H', subr.prod_id, subr.os_short_name,
	 updateday
FROM (
		   SELECT distinct hangid, product_version_id AS prod_id, substring(os_name, 1, 3) AS os_short_name
			FROM product_versions
			JOIN reports on product_versions.product_name = reports.product::citext
				AND product_versions.version_string = reports.version::citext
			WHERE date_processed >= utc_day_begins_pacific(updateday)
					AND date_processed < utc_day_ends_pacific(updateday)
                AND ( lower(release_channel) NOT IN ( 'nightly', 'beta', 'aurora' )
                      or release_channel is null )
				AND updateday BETWEEN product_versions.build_date and sunset_date
			AND product_versions.build_type <> 'beta'
            AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
		 ) AS subr
GROUP BY subr.prod_id, subr.os_short_name;

-- insert normalized hangs for new products
-- beta
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT count(subr.hangid) as count, 'H', subr.prod_id, subr.os_short_name,
	 updateday
FROM (
		   SELECT distinct hangid, product_version_id AS prod_id, substring(os_name, 1, 3) AS os_short_name
			FROM product_versions
			JOIN reports on product_versions.product_name = reports.product::citext
				AND product_versions.release_version = reports.version::citext
			WHERE date_processed >= utc_day_begins_pacific(updateday)
					AND date_processed < utc_day_ends_pacific(updateday)
                AND release_channel ILIKE 'beta'
				AND updateday BETWEEN product_versions.build_date and sunset_date
                AND EXISTS (SELECT 1
                    FROM product_version_builds
                    WHERE product_versions.product_version_id = product_version_builds.product_version_id
                      AND product_version_builds.build_id = build_numeric(reports.build) )
			AND product_versions.build_type = 'beta'
            AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
		 ) AS subr
GROUP BY subr.prod_id, subr.os_short_name;

ANALYZE daily_crashes;

RETURN TRUE;

END;$f$;


create or replace function update_tcbs (
	updateday date )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
AS $f$
BEGIN
-- this procedure goes throught the daily TCBS update for the
-- new TCBS table
-- designed to be run only once for each day
-- attempts to run it a second time will error
-- needs to be run last after most other updates

-- check that it hasn't already been run

PERFORM 1 FROM tcbs
WHERE report_date = updateday LIMIT 1;
IF FOUND THEN
	RAISE EXCEPTION 'TCBS has already been run for the day %.',updateday;
END IF;

-- create a temporary table

CREATE TEMPORARY TABLE new_tcbs
ON COMMIT DROP AS
SELECT signature, 
	product::citext as product, 
	version::citext as version, 
	build,
	release_channel::citext as release_channel, 
	os_name::citext as os_name, 
	os_version::citext as os_version,
	process_type::citext as process_type, 
	count(*) as report_count,
	0::int as product_version_id,
	0::int as signature_id,
	null::citext as real_release_channel,
    SUM(case when hangid is not null then 1 else 0 end) as hang_count
FROM reports
WHERE date_processed >= utc_day_begins_pacific(updateday)
	and date_processed <= utc_day_begins_pacific((updateday + 1))
GROUP BY signature, product::citext, version::citext, build,
	release_channel::citext, os_name::citext, os_version::citext,
	process_type::citext;

PERFORM 1 FROM new_tcbs LIMIT 1;
IF NOT FOUND THEN
	RAISE EXCEPTION 'no report data found for TCBS for date %', updateday;
END IF;

ANALYZE new_tcbs;

-- clean process_type

UPDATE new_tcbs
SET process_type = 'Browser'
WHERE process_type IS NULL
	OR process_type = '';

-- clean release_channel

UPDATE new_tcbs
SET real_release_channel = release_channels.release_channel
FROM release_channels
	JOIN release_channel_matches ON
		release_channels.release_channel = release_channel_matches.release_channel
WHERE new_tcbs.release_channel ILIKE match_string;

UPDATE new_tcbs SET real_release_channel = 'Release'
WHERE real_release_channel IS NULL;

-- populate signature_id

UPDATE new_tcbs SET signature_id = signatures.signature_id
FROM signatures
WHERE COALESCE(new_tcbs.signature,'') = signatures.signature;

-- populate product_version_id for betas

UPDATE new_tcbs
SET product_version_id = product_versions.product_version_id
FROM product_versions
	JOIN product_version_builds ON product_versions.product_version_id = product_version_builds.product_version_id
WHERE product_versions.build_type = 'Beta'
    AND new_tcbs.real_release_channel = 'Beta'
	AND new_tcbs.product = product_versions.product_name
	AND new_tcbs.version = product_versions.release_version
	AND build_numeric(new_tcbs.build) = product_version_builds.build_id;

-- populate product_version_id for other builds

UPDATE new_tcbs
SET product_version_id = product_versions.product_version_id
FROM product_versions
WHERE product_versions.build_type <> 'Beta'
    AND new_tcbs.real_release_channel <> 'Beta'
	AND new_tcbs.product = product_versions.product_name
	AND new_tcbs.version = product_versions.release_version
	AND new_tcbs.product_version_id = 0;

-- if there's no product and version still, or no
-- signature, discard
-- since we can't report on it

DELETE FROM new_tcbs WHERE product_version_id = 0
  OR signature_id = 0;

-- fix os_name

UPDATE new_tcbs SET os_name = os_name_matches.os_name
FROM os_name_matches
WHERE new_tcbs.os_name ILIKE match_string;

-- populate the matview

INSERT INTO tcbs (
	signature_id, report_date, product_version_id,
	process_type, release_channel,
	report_count, win_count, mac_count, lin_count, hang_count
)
SELECT signature_id, updateday, product_version_id,
	process_type, real_release_channel,
	sum(report_count),
	sum(case when os_name = 'Windows' THEN report_count else 0 END),
	sum(case when os_name = 'Mac OS X' THEN report_count else 0 END),
	sum(case when os_name = 'Linux' THEN report_count else 0 END),
    sum(hang_count)
FROM new_tcbs
GROUP BY signature_id, updateday, product_version_id,
	process_type, real_release_channel;

ANALYZE tcbs;

-- update tcbs_ranking based on tcbs
-- this fills in per day for four aggregation levels

-- all crashes

INSERT INTO tcbs_ranking (
	product_version_id, signature_id,
	process_type, release_channel,
	aggregation_level,
	total_reports, rank_report_count )
SELECT product_version_id, signature_id,
	NULL, NULL,
	'All',
	sum(report_count) over () as total_count,
	dense_rank() over (order by report_count desc) as tcbs_rank
FROM (
	SELECT product_version_id, signature_id,
	sum(report_count) as report_count
	FROM tcbs
	WHERE report_date = updateday
	GROUP BY product_version_id, signature_id
) as tcbs_r;

-- group by process_type

INSERT INTO tcbs_ranking (
	product_version_id, signature_id,
	process_type, release_channel,
	aggregation_level,
	total_reports, rank_report_count )
SELECT product_version_id, signature_id,
	process_type, NULL,
	'process_type',
	sum(report_count) over () as total_count,
	dense_rank() over (order by report_count desc) as tcbs_rank
FROM (
	SELECT product_version_id, signature_id,
	process_type,
	sum(report_count) as report_count
	FROM tcbs
	WHERE report_date = updateday
	GROUP BY product_version_id, signature_id, process_type
) as tcbs_r;

-- group by release_channel

INSERT INTO tcbs_ranking (
	product_version_id, signature_id,
	process_type, release_channel,
	aggregation_level,
	total_reports, rank_report_count )
SELECT product_version_id, signature_id,
	NULL, release_channel,
	'All',
	sum(report_count) over () as total_count,
	dense_rank() over (order by report_count desc) as tcbs_rank
FROM (
	SELECT product_version_id, signature_id, release_channel,
	sum(report_count) as report_count
	FROM tcbs
	WHERE report_date = updateday
	GROUP BY product_version_id, signature_id, release_channel
) as tcbs_r;

-- group by process_type and release_channel

INSERT INTO tcbs_ranking (
	product_version_id, signature_id,
	process_type, release_channel,
	aggregation_level,
	total_reports, rank_report_count )
SELECT product_version_id, signature_id,
	NULL, NULL,
	'All',
	sum(report_count) over () as total_count,
	dense_rank() over (order by report_count desc) as tcbs_rank
FROM (
	SELECT product_version_id, signature_id,
		process_type, release_channel,
	sum(report_count) as report_count
	FROM tcbs
	WHERE report_date = updateday
	GROUP BY product_version_id, signature_id,
		process_type, release_channel
) as tcbs_r;

-- done
RETURN TRUE;
END;
$f$;
