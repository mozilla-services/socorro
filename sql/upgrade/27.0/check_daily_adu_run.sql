BEGIN;

DROP TABLE IF EXISTS raw_adu_status;

CREATE TABLE raw_adu_status (
    last_check TIMESTAMPTZ NOT NULL
    , is_good BOOLEAN NOT NULL
);

CREATE OR REPLACE FUNCTION check_raw_adu(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $function$
BEGIN

PERFORM 1 FROM raw_adu_status
WHERE last_check::date = updateday
AND is_good
LIMIT 1;

IF NOT FOUND THEN
    -- We did not find a successful raw_adu check for updateday
    -- so run the check now
    PERFORM 1 FROM raw_adu
    WHERE "date" = updateday
    LIMIT 1;

    IF NOT FOUND THEN
        INSERT INTO raw_adu_status VALUES(now(), False);
        RETURN FALSE;
    ELSE
        INSERT INTO raw_adu_status VALUES(now(), True);
        RETURN TRUE;
    END IF;
ELSE
    RETURN TRUE;
END IF;

-- Delete data that is older than 30 days to keep table small
DELETE FROM raw_adu_status WHERE last_check < (now() - '30 days'::interval);

END; $function$;

COMMIT;
