create or replace function backfill_tcbs (
	updateday date, forproduct text default '' )
RETURNS BOOLEAN
LANGUAGE plpgsql 
SET work_mem = '512MB'
SET temp_buffers = '512MB'
AS $f$
BEGIN
-- deletes and replaces rows in tcbs for the selected day
-- and optional product
-- intended to be called administratively by backfill_matviews

-- delete old rows

DELETE FROM tcbs
USING product_versions
WHERE report_date = updateday
  AND tcbs.product_version_id = product_versions.product_version_id
  AND ( product_name = forproduct or forproduct = '' );

-- create a temporary table

CREATE TEMPORARY TABLE new_tcbs
ON COMMIT DROP AS
SELECT signature, product, version, build,
	release_channel, os_name, os_version,
	process_type, count(*) as report_count,
	0::int as product_version_id,
	0::int as signature_id,
	null::citext as real_release_channel,
    SUM(case when hangid is not null then 1 else 0 end) as hang_count
FROM reports
WHERE date_processed >= utc_day_begins_pacific(updateday)
	and date_processed <= utc_day_begins_pacific((updateday + 1))
GROUP BY signature, product, version, build,
	release_channel, os_name, os_version,
	process_type;

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

-- done
RETURN TRUE;
END;
$f$;
