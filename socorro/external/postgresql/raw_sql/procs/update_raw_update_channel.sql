CREATE OR REPLACE FUNCTION update_raw_update_channel(
    fromtime timestamp with time zone,
    fortime interval DEFAULT '01:00:00'::interval,
    checkdata boolean DEFAULT true,
    analyze_it boolean DEFAULT true,
    forproduct TEXT DEFAULT 'b2g'
)
    RETURNS boolean
    LANGUAGE plpgsql
    SET "TimeZone" TO 'UTC'
AS $_$
DECLARE
    newfortime INTERVAL;
BEGIN

-- Updates raw_update_channel with latest 'release_channel' or 'update_channel' data
-- designed to be run hourly
-- running it repeatedly won't cause issues
-- ignores NULL and empty release_channel/update_channel
-- Only checks for new update_channels reported in the last hour

IF (week_begins_utc(fromtime) <> week_begins_utc(fromtime + fortime - interval '1 second')) THEN
    PERFORM update_raw_update_channel(
        fromtime,
        (week_begins_utc(fromtime + fortime) - fromtime),
        checkdata);
    newfortime := (fromtime + fortime) - week_begins_utc(fromtime + fortime);
    fromtime := week_begins_utc(fromtime + fortime);
    fortime := newfortime;
END IF;

-- prevent calling for a period of more than one day

IF fortime > INTERVAL '1 day' THEN
    RAISE NOTICE 'You may not execute this function on more than one day of data';
    RETURN FALSE;
END IF;

-- create temporary table

CREATE TEMPORARY TABLE update_channels_recent
ON commit drop AS
SELECT coalesce(release_channel, update_channel, '') as update_channel,
    lower(product) as product_name,
    version::text as version,
    build::numeric,
    min(date_processed) as first_report
FROM reports
WHERE date_processed >= fromtime and date_processed < (fromtime + fortime)
AND lower(product) = lower(forproduct)
group by coalesce(release_channel, update_channel, ''), product, version, build;

PERFORM 1 FROM update_channels_recent;
IF NOT FOUND THEN
    IF checkdata THEN
        RAISE NOTICE 'no update_channels data found in reports for date %', fromtime;
        RETURN FALSE;
    END IF;
END IF;

INSERT INTO raw_update_channels (
    update_channel,
    product_name,
    version,
    build,
    first_report
)
SELECT
    ucr.update_channel,
    ucr.product_name,
    ucr.version,
    ucr.build,
    ucr.first_report
from update_channels_recent ucr
LEFT OUTER JOIN raw_update_channels ruc
    ON ucr.update_channel = ruc.update_channel
    and ucr.product_name = ruc.product_name
    and ucr.version = ruc.version
    and ucr.build = ruc.build
WHERE
    ruc.first_report IS NULL
    AND ucr.update_channel IS NOT NULL;

DROP TABLE update_channels_recent;

RETURN TRUE;

END;
$_$;
