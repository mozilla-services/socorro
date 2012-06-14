/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
