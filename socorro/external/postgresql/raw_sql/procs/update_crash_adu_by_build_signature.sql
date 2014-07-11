CREATE OR REPLACE FUNCTION update_crash_adu_by_build_signature(
    updateday date,
    checkdata boolean DEFAULT true
)
    RETURNS boolean
    LANGUAGE plpgsql
    SET "TimeZone" to 'UTC'
AS $$
BEGIN

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM crash_adu_by_build_signature WHERE adu_date = updateday LIMIT 1;
    IF FOUND THEN
        RAISE INFO 'update_crash_adu_by_build_signature() has already been run for %.', updateday;
    END IF;
END IF;


CREATE TEMPORARY TABLE new_build_adus
AS
    WITH build_adus AS (
        SELECT
            product_version_id,
            adu_date,
            SUM(adu_count) AS aducount,
            build_date,
            os_name
        FROM build_adu
        WHERE adu_date BETWEEN updateday and updateday + 1
        GROUP BY product_version_id,
            adu_date,
            build_date,
            os_name
    ),
    sigreports AS (
        SELECT
            product_version_id,
            build,
            COUNT(*) AS crashcount,
            release_channel,
            reports_clean.signature_id,
            signatures.signature as signature,
            os_name
        FROM reports_clean
            JOIN signatures ON reports_clean.signature_id = signatures.signature_id
        WHERE
            date_processed BETWEEN updateday and updateday + 1
            AND length(reports_clean.build::text) >= 8
        GROUP BY
            product_version_id,
            build,
            reports_clean.signature_id,
            signatures.signature,
            os_name,
            release_channel
    )
    SELECT
        build_adus.build_date as build_date,
        SUM(build_adus.aducount) as adu_count,
        build_adus.os_name as os_name,
        build_adus.adu_date as adu_date,
        COALESCE(sigreports.release_channel, pv.build_type) as channel,
        COALESCE(sigreports.signature_id, 0) as signature_id,
        COALESCE(sigreports.signature, '') as signature,
        COALESCE(sigreports.build, 0) as buildid,
        pv.product_name as product_name,
        COALESCE(SUM(sigreports.crashcount), 0) as crash_count
    FROM build_adus
        LEFT OUTER JOIN sigreports ON
            sigreports.product_version_id = build_adus.product_version_id AND
            to_date(substring(sigreports.build::text from 1 for 8), 'YYYYMMDD') = build_adus.build_date AND
            sigreports.os_name = build_adus.os_name
        JOIN product_versions pv ON build_adus.product_version_id = pv.product_version_id
    WHERE length(build_adus.build_date::text) >= 8
    GROUP BY
        build_adus.build_date,
        build_adus.os_name,
        build_adus.adu_date,
        sigreports.release_channel,
        sigreports.signature_id,
        sigreports.signature,
        sigreports.build,
        pv.product_name,
        pv.build_type
;

PERFORM 1 FROM new_build_adus;
IF NOT FOUND THEN
    IF checkdata THEN
        RAISE NOTICE 'no new build adus for day %', updateday;
        RETURN FALSE;
    END IF;
END IF;

ANALYZE new_build_adus;

INSERT INTO crash_adu_by_build_signature (
    signature_id,
    signature,
    adu_date,
    build_date,
    buildid,
    crash_count,
    adu_count,
    os_name,
    channel,
    product_name
)
SELECT
    new_build_adus.signature_id,
    new_build_adus.signature,
    new_build_adus.adu_date,
    new_build_adus.build_date,
    new_build_adus.buildid,
    new_build_adus.crash_count,
    new_build_adus.adu_count,
    new_build_adus.os_name,
    new_build_adus.channel,
    new_build_adus.product_name
FROM
    new_build_adus
;

DROP TABLE new_build_adus;

RETURN True;

END;
$$;
