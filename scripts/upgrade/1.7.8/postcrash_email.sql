-- bug 612596
\set ON_ERROR_STOP true

BEGIN;
ALTER TABLE email_contacts ADD COLUMN ooid TEXT;
ALTER TABLE email_contacts ADD COLUMN crash_date TIMESTAMP with time zone;
COMMIT;
