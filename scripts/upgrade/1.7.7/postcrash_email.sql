-- bug 630350
\set ON_ERROR_STOP true

BEGIN;
-- create tables.  default campaigns as sent since we assume existing onese
-- were already sent
ALTER TABLE email_campaigns ADD COLUMN status NOT NULL DEFAULT 'sent'
ALTER TABLE email_campaigns_contacts ADD COLUMN status NOT NULL DEFAULT 'ready'
-- now change default to stopped for new records
ALTER TABLE email_campaigns_contacts ALTER COLUMN status DEFAULT 'stopped';
COMMIT;
