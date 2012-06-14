/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

BEGIN;

ALTER TABLE socorro_db_version_history DROP CONSTRAINT socorro_db_version_history_pkey;

ALTER TABLE socorro_db_version_history ADD CONSTRAINT socorro_db_version_history_pkey PRIMARY KEY (version, upgraded_on);

COMMIT;

CREATE OR REPLACE FUNCTION update_socorro_db_version (
	newversion TEXT, backfilldate DATE default NULL )
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $f$
DECLARE rerun BOOLEAN;
BEGIN
	SELECT current_version = newversion
	INTO rerun
	FROM socorro_db_version;
	
	IF rerun THEN
		RAISE NOTICE 'This database is already set to version %.  If you have deliberately rerun the upgrade scripts, then this is as expected.  If not, then there is something wrong.',newversion;
	ELSE
		UPDATE socorro_db_version SET current_version = newversion;
	END IF;
	
	INSERT INTO socorro_db_version_history ( version, upgraded_on, backfill_to )
		VALUES ( newversion, now(), backfilldate );
	
	RETURN true;
END; $f$;

	