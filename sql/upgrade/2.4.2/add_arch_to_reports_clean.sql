/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

DO $f$
BEGIN

PERFORM 1 FROM information_schema.columns
	WHERE table_name = 'reports_clean'
	AND column_name = 'architecture';

IF NOT FOUND THEN
	ALTER TABLE reports_clean ADD architecture CITEXT;
	ALTER TABLE reports_clean ADD cores INT;
END IF;

END;
$f$;
