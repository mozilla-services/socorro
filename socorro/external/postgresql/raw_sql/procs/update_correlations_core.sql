CREATE OR REPLACE FUNCTION update_correlations_core(
    updateday date,
    checkdata boolean DEFAULT true,
    check_period interval DEFAULT '01:00:00'::interval
)
    RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $$
BEGIN
-- this function populates daily matviews
-- for some of the correlation reports
-- depends on reports_clean, product_versions and processed_crashes

-- check if correlations has already been run for the date
PERFORM 1 FROM correlations_core
WHERE report_date = updateday LIMIT 1;
IF FOUND THEN
  IF checkdata THEN
      RAISE NOTICE 'update_correlations has already been run for %', updateday;
  END IF;
  RETURN FALSE;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE NOTICE 'Reports_clean has not been updated to the end of %',updateday;
        RETURN FALSE;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

--populate correlations_core matview
WITH crash AS (
    SELECT processed_crash->'json_dump'->'system_info' AS system_info
           , product_version_id
           , signature_id
           , reason_id
           , reports_clean.date_processed::date
           , reports_clean.os_name
    FROM processed_crashes
    JOIN reports_clean ON (processed_crashes.uuid::text = reports_clean.uuid)
    JOIN product_versions USING (product_version_id)
    WHERE reports_clean.date_processed
        BETWEEN updateday::timestamptz AND updateday::timestamptz + '1 day'::interval
    AND processed_crashes.date_processed -- also need to filter on date_processed
        BETWEEN updateday::timestamptz AND updateday::timestamptz + '1 day'::interval
    AND sunset_date > now()
)
INSERT INTO correlations_core (
    product_version_id
    , cpu_arch
    , cpu_count
    , report_date
    , os_name
    , signature_id
    , reason_id
    , total
)
SELECT product_version_id
       , (system_info->'cpu_arch')::text as cpu_arch
       , (system_info->'cpu_count')::text as cpu_count
       , date_processed as report_date
       , os_name
       , signature_id
       , reason_id
       , count(*) as total
FROM crash
WHERE (system_info->'cpu_arch')::text IS NOT null
AND (system_info->'cpu_count')::text IS NOT null
GROUP BY cpu_arch
         , cpu_count
         , product_version_id
         , report_date
         , os_name
         , signature_id
         , reason_id;
RETURN TRUE;
END;
$$;
