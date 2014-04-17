CREATE OR REPLACE FUNCTION update_signatures(
    updateday date,
    checkdata boolean DEFAULT true
)
    RETURNS boolean
    LANGUAGE plpgsql
    SET "TimeZone" TO 'UTC'
AS $$
BEGIN

-- Function for updating signature information post-rapid-release
-- designed to be run once per UTC day.
-- running it repeatedly won't cause issues
-- combines NULL and empty signatures

-- Now uses update_signatures_hourly() as base function
PERFORM update_signatures_hourly(
    updateday::timestamp AT TIME ZONE 'UTC',
    '24:00:00',
    checkdata
);

RETURN TRUE;
END;
$$;
