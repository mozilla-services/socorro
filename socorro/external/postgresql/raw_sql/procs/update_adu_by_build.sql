CREATE OR REPLACE FUNCTION update_adu_by_build(updateday date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET "TimeZone" to 'UTC'
    AS $$
BEGIN

CREATE TEMPORARY TABLE new_build_adus
AS
    WITH build_adus AS (
        SELECT 
            build_date,
            SUM(adu_count) AS aducount,
            os_name,
            adu_date
        FROM build_adu
        WHERE adu_date >= updateday AND adu_date < updateday + 1
        GROUP BY product_version_id, build_date, os_name, adu_date
    ),
    sigreports AS (
        SELECT 
            build, 
            COUNT(*) AS crashcount,
            os_name,
            signatures.signature_id as signature_id
        FROM reports_clean
        JOIN signatures ON reports_clean.signature_id = signatures.signature_id
        WHERE
            date_processed >= updateday AND date_processed < updateday + 1
        GROUP BY build, os_name, signatures.signature_id
    )
    SELECT
        build_adus.build_date as build_date,
        build_adus.aducount as adu_count,
        build_adus.os_name as os_name,
        build_adus.adu_date as adu_date,
        sigreports.signature_id as signature_id,
        sigreports.build as buildid,
        sigreports.crashcount as crash_count
    FROM build_adus
    JOIN sigreports ON sigreports.os_name = build_adus.os_name AND 
    to_date(substring(sigreports.build::text from 1 for 8), 'YYYYMMDD') = build_adus.build_date
;

PERFORM 1 FROM new_build_adus;
IF NOT FOUND THEN
    IF checkdata THEN
        RAISE NOTICE 'no new build adus for day %', updateday;
        RETURN FALSE;
    END IF;
END IF;

ANALYZE new_build_adus;

INSERT INTO adu_by_build (
    signature_id,
    adu_date,
    build_date,
    buildid,
    crash_count,
    adu_count,
    os_name
)
SELECT
    new_build_adus.signature_id,
    new_build_adus.adu_date,
    new_build_adus.build_date,
    new_build_adus.buildid,
    new_build_adus.crash_count,
    new_build_adus.adu_count,
    new_build_adus.os_name
FROM 
    new_build_adus
;

DROP TABLE new_build_adus;

RETURN True;

END;
$$;
