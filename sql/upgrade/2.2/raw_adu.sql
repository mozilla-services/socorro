/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

-- adds build id to raw_adu and removes os_version

BEGIN;

ALTER TABLE raw_adu ADD COLUMN build TEXT;
ALTER TABLE raw_adu ADD COLUMN build_channel TEXT;

COMMIT;
