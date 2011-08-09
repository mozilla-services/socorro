\set ON_ERROR_STOP 1

-- adds build id to raw_adu and removes os_version

BEGIN;

ALTER TABLE raw_adu ADD COLUMN build TEXT;
ALTER TABLE raw_adu ADD COLUMN build_channel TEXT;

COMMIT;