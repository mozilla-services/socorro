CREATE TABLE hang_report(
    product TEXT,
    version TEXT,
    browser_signature TEXT,
    plugin_signature TEXT,
    browser_hangid TEXT,
    flash_version TEXT,
    url TEXT,
    uuid TEXT,
    duplicates TEXT[],
    report_day DATE);

GRANT ALL ON hang_report TO breakpad_rw;

CREATE OR REPLACE FUNCTION update_hang_report(updateday DATE) RETURNS BOOLEAN
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET maintenance_work_mem TO '512MB'
    AS $$
    BEGIN
    -- daily batch update function for hang/crash pair report
    -- created for bug 637661

    INSERT INTO hang_report (
        SELECT
            product_name AS product,
            version_string AS version,
            browser.signature AS browser_signature,
            plugin.signature AS plugin_signature,
            browser.hangid AS browser_hangid,
            browser.flash_version AS flash_version,
            browser.url AS url,
            browser.uuid AS uuid,
            ARRAY(
                SELECT dups.uuid
                FROM reports_duplicates AS dups
                WHERE browser.uuid = dups.uuid
            ) AS duplicates,
            updateday AS report_day
        FROM reports AS browser
        JOIN reports AS plugin ON plugin.hangid = browser.hangid
        JOIN product_version_builds AS pvb
          ON browser.build::NUMERIC = pvb.build_id
        JOIN product_versions AS pv
          ON pvb.product_version_id = pv.product_version_id
        WHERE plugin.signature LIKE 'hang | %'
        AND browser.hangid != ''
        AND browser.process_type IS NULL
        AND plugin.process_type = 'plugin'
        AND browser.signature != plugin.signature
        AND browser.date_processed > utc_day_begins_pacific(updateday)
        AND browser.date_processed < utc_day_ends_pacific(updateday)
    );

    ANALYZE hang_report;

    RETURN TRUE;
    END;
$$;
