-- bug 630350
ALTER TABLE email_campaigns ADD COLUMN status NOT NULL DEFAULT 'stopped'
ALTER TABLE email_campaigns_contacts ADD COLUMN status NOT NULL DEFAULT 'ready'
-- set all existing campaigns as 'sent', so they can't be accidentally re-sent
UPDATE email_campaigns_contacts SET status = 'sent';

