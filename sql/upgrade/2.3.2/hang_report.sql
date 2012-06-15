\set ON_ERROR_STOP 1

DROP TABLE IF EXISTS hang_report;

SELECT create_table_if_not_exists ( 'daily_hangs', $x$
CREATE TABLE daily_hangs (
	uuid text not null,
	plugin_uuid text not null primary key,
	report_date date,
	product_version_id int not null,
	browser_signature_id int not null,
	plugin_signature_id int not null,
	hang_id text not null,
	flash_version_id int,
	url citext,
	duplicates text[]
);$x$,
'breakpad_rw',
ARRAY[ 'report_date', 'uuid', 'product_version_id', 'browser_signature_id', 
	'plugin_signature_id', 'flash_version_id', 'hang_id' ] );

CREATE OR REPLACE FUNCTION update_hang_report (
	updateday date, checkdata boolean default true )
RETURNS boolean
LANGUAGE plpgsql
SET work_mem = '512MB'
SET maintenance_work_mem = '512MB'
AS $f$
BEGIN

-- check if we have reports_clean data
PERFORM 1 FROM reports_clean 
WHERE utc_day_is(date_processed, updateday) LIMIT 1;
IF NOT FOUND THEN
	IF checkdata THEN
		RAISE EXCEPTION 'no reports_clean data found for date %',updateday;
	ELSE
		RETURN TRUE;
	END IF;
END IF;
-- check if we already have hang data
PERFORM 1 FROM daily_hangs
WHERE report_date = updateday LIMIT 1;
IF FOUND THEN
	RAISE EXCEPTION 'it appears that hang_report has already been run for %.  If you are backfilling, use backfill_hang_report instead.',updateday;
END IF;

-- insert data
-- note that we need to group on the plugin here and
-- take min() of all of the browser crash data.  this is a sloppy
-- approach but works because the only reason for more than one 
-- browser crash in a hang group is duplicate crash data
INSERT INTO daily_hangs ( uuid, plugin_uuid, report_date,
	product_version_id, browser_signature_id, plugin_signature_id,
	hang_id, flash_version_id, duplicates, url )
SELECT
    min(browser.uuid) ,
    plugin.uuid,
    updateday as report_date,
    min(browser.product_version_id),
    min(browser.signature_id),
    plugin.signature_id AS plugin_signature_id,
    plugin.hang_id,
    plugin.flash_version_id,
    nullif(array_agg(browser.duplicate_of) 
    	|| COALESCE(ARRAY[plugin.duplicate_of], '{}'),'{NULL}'),
    min(browser_info.url)
FROM reports_clean AS browser
    JOIN reports_clean AS plugin ON plugin.hang_id = browser.hang_id
    LEFT OUTER JOIN reports_user_info AS browser_info ON browser.uuid = browser_info.uuid
    JOIN signatures AS sig_browser
        ON sig_browser.signature_id = browser.signature_id
WHERE sig_browser.signature LIKE 'hang | %'
    AND browser.hang_id != ''
    AND browser.process_type = 'browser'
    AND plugin.process_type = 'plugin'
    AND utc_day_near(browser.date_processed, updateday)
    AND utc_day_is(plugin.date_processed, updateday)
    AND utc_day_is(browser_info.date_processed, updateday)
GROUP BY plugin.uuid, plugin.signature_id, plugin.hang_id, plugin.flash_version_id,
	plugin.duplicate_of;
    
ANALYZE daily_hangs;
RETURN TRUE;
END;$f$;

CREATE OR REPLACE FUNCTION backfill_hang_report (
	backfilldate date )
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $f$
BEGIN
-- delete rows
DELETE FROM daily_hangs
WHERE report_date = backfilldate;

PERFORM update_hang_report(backfilldate, false);
RETURN TRUE;

END;
$f$;

CREATE VIEW hang_report
AS 
SELECT
	product_name AS product,
	version_string AS version,
	browser_signatures.signature AS browser_signature,
	plugin_signatures.signature AS plugin_signature,
	hang_id AS browser_hangid,
	flash_version,
	url,
	uuid,
	duplicates,
	report_date as report_day
FROM daily_hangs
JOIN product_versions USING (product_version_id)
JOIN signatures as browser_signatures ON browser_signature_id = browser_signatures.signature_id
JOIN signatures AS plugin_signatures ON plugin_signature_id = plugin_signatures.signature_id
LEFT OUTER JOIN flash_versions USING (flash_version_id);









