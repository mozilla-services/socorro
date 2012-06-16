/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

-- bug 630350
\set ON_ERROR_STOP true

BEGIN;
ALTER TABLE email_campaigns ALTER COLUMN status SET DEFAULT 'stopped';
COMMIT;
