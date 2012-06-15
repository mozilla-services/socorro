-- bug 630350
\set ON_ERROR_STOP true

BEGIN;
-- create tables.  default campaigns as sent since we assume existing onese
-- were already sent
ALTER TABLE email_campaigns ADD COLUMN status TEXT DEFAULT 'sent';
ALTER TABLE email_campaigns_contacts ADD COLUMN status TEXT DEFAULT 'ready';
ALTER TABLE email_campaigns ALTER COLUMN status SET NOT NULL;
ALTER TABLE email_campaigns_contacts ALTER COLUMN status SET NOT NULL;
-- now change default to stopped for new records
ALTER TABLE email_campaigns_contacts ALTER COLUMN status SET DEFAULT 'stopped';
COMMIT;
