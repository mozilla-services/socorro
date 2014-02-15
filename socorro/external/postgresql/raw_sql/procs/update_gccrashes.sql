CREATE OR REPLACE FUNCTION update_gccrashes(
    updateday date,
    checkdata boolean DEFAULT true,
    check_period interval DEFAULT '01:00:00'::interval
) RETURNS boolean
    LANGUAGE plpgsql
    SET client_min_messages TO 'ERROR'
AS $$
BEGIN
-- this procedure goes through raw crashes and creates a matview with count of
-- is_gc annotated crashes per build ID
-- designed to be run only once for each day

-- check that it hasn't already been run

IF checkdata THEN
    PERFORM 1 FROM gccrashes
    WHERE report_date = updateday LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'gccrashes has already been run for the day %.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE NOTICE 'Reports_clean has not been updated to the end of %',updateday;
        RETURN FALSE;
    ELSE
        RAISE INFO 'reports_clean not updated';
        RETURN FALSE;
    END IF;
END IF;

INSERT INTO gccrashes (
    report_date,
    product_version_id,
    build,
    gc_count_madu
)
WITH raw_crash_filtered AS (
    SELECT
          uuid
        , json_object_field_text(r.raw_crash, 'IsGarbageCollecting') as is_garbage_collecting
    FROM
        raw_crashes r
    WHERE
        date_processed BETWEEN updateday::timestamptz
            AND updateday::timestamptz + '1 day'::interval
)
SELECT updateday
    , product_version_id
    , build
    , crash_madu(sum(CASE WHEN r.is_garbage_collecting = '1' THEN 1 ELSE 0 END), sum(adu_count), 1) as gc_count_madu
FROM reports_clean
    JOIN product_versions USING (product_version_id)
    JOIN build_adu USING (product_version_id)
    LEFT JOIN raw_crash_filtered r ON r.uuid::text = reports_clean.uuid
WHERE utc_day_is(date_processed, updateday)
        AND tstz_between(date_processed, build_date(build), sunset_date)
        AND product_versions.build_type = 'nightly'
        AND tstz_between(adu_date, build_date(build), sunset_date)
        AND adu_count > 0
        AND build_date(build) = build_adu.build_date
        AND date_processed - build_date(build) < '7 days'::interval
        AND length(build::text) >= 10
GROUP BY build, product_version_id
ORDER BY build;

RETURN TRUE;
END;
$$;
