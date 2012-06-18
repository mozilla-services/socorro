/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

DO $f$
BEGIN
PERFORM 1 FROM information_schema.columns
WHERE table_name = 'releases_raw' AND column_name = 'repository';
IF NOT FOUND THEN
	ALTER TABLE releases_raw ADD COLUMN repository CITEXT;
	UPDATE releases_raw SET repository = 'mozilla-release' WHERE repository IS NULL;
	ALTER TABLE releases_raw ALTER COLUMN repository SET DEFAULT 'mozilla-release';
	ALTER TABLE releases_raw DROP CONSTRAINT release_raw_key;
	ALTER TABLE releases_raw 
		ADD CONSTRAINT release_raw_key PRIMARY KEY ( product_name, version, build_type, build_id, platform, repository);
	CREATE INDEX releases_raw_date ON releases_raw((build_date(build_id)));
END IF;
END;
$f$;