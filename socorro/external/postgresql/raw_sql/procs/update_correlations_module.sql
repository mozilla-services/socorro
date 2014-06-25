CREATE OR REPLACE FUNCTION update_correlations_module(
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
PERFORM 1 FROM correlations_module
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

INSERT INTO modules (name, version) (
    SELECT (json_array_elements(processed_crash->'json_dump'->'modules')->'filename')::text as name
           , (json_array_elements(processed_crash->'json_dump'->'modules')->'debug_file')::text as version
    FROM processed_crashes
    JOIN reports_clean ON (processed_crashes.uuid::text = reports_clean.uuid)
    JOIN product_versions USING (product_version_id)
    WHERE reports_clean.date_processed
        BETWEEN updateday::timestamptz AND updateday::timestamptz + '1 day'::interval
    AND processed_crashes.date_processed -- also need to filter on date_processed
        BETWEEN updateday::timestamptz AND updateday::timestamptz + '1 day'::interval
    AND sunset_date > now()
    AND NOT EXISTS (SELECT name,version FROM modules WHERE name = name AND version = version)
    GROUP BY name, version
);

--create correlations_module matview
WITH crash AS (
    SELECT json_array_elements(processed_crash->'json_dump'->'modules') AS module
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
INSERT INTO correlations_module (
    product_version_id
    , module_id
    , report_date
    , os_name
    , signature_id
    , reason_id
    , total
)
SELECT product_version_id
       , module_id
       , date_processed as report_date
       , os_name
       , signature_id
       , reason_id
       , count(*) as total
FROM crash
    JOIN modules
        ON (module->'filename')::text = modules.name
        AND (module->'debug_file')::text = modules.version
WHERE
    (module->'filename')::text IS NOT NULL
AND (module->'debug_file')::text IS NOT NULL
GROUP BY module_id
         , product_version_id
         , report_date
         , os_name
         , signature_id
         , reason_id;

RETURN TRUE;
END;
$$;
