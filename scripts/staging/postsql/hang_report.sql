
CREATE OR REPLACE VIEW hang_report
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

ALTER VIEW hang_report OWNER TO breakpad_rw;



