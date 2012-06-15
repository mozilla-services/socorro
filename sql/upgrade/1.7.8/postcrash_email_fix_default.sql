-- bug 630350
\set ON_ERROR_STOP true

BEGIN;
ALTER TABLE email_campaigns ALTER COLUMN status SET DEFAULT 'stopped';
COMMIT;
