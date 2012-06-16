/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

BEGIN;

SELECT create_table_if_not_exists ( 'windows_versions', $x$
CREATE TABLE windows_versions (
	windows_version_name citext not null,
	major_version INT not null,
	minor_version INT not null,
	constraint windows_version_key unique ( major_version, minor_version )
);$x$, 'breakpad_rw' );

INSERT INTO windows_versions VALUES
	(  'Windows NT',  3, 5 ),
	( 'Windows NT', 4, 0 ),
	( 'Windows 98', 4, 1 ),
	( 'Windows Me', 4, 9 ),
	( 'Windows 2000', 5, 0 ),
	( 'Windows XP', 5, 1  ),
	( 'Windows Vista', 6, 0 ),
	( 'Windows 7', 6, 1 );

ALTER TABLE os_versions ADD COLUMN os_version_string citext;
	
CREATE OR REPLACE FUNCTION create_os_version_string (
	osname citext, major int, minor int)
RETURNS citext 
LANGUAGE plpgsql
STABLE STRICT AS $f$
DECLARE winversion CITEXT;
BEGIN
	-- small function which produces a user-friendly
	-- string for the operating system and version
	-- if windows, look it up in windows_versions
	IF osname = 'Windows' THEN
		SELECT windows_version_name INTO winversion
		FROM windows_versions
		WHERE major_version = major AND minor_version = minor;
		IF NOT FOUND THEN
			RETURN 'Windows Unknown';
		ELSE
			RETURN winversion;
		END IF;
	ELSEIF osname = 'Mac OS X' THEN
	-- if mac, then concatinate unless the numbers are impossible
		IF major BETWEEN 10 and 11 AND minor BETWEEN 0 and 20 THEN
			RETURN 'OS X ' || major || '.' || minor;
		ELSE
			RETURN 'OS X Unknown';
		END IF;
	ELSE
	-- for other oses, just use the OS name
		RETURN osname;
	END IF;
END; $f$;
		
UPDATE os_versions SET os_version_string 
	= create_os_version_string( os_name, major_version, minor_version )
WHERE os_version_string IS NULL;
	
ANALYZE os_versions;
ANALYZE windows_versions;

END;






	
	