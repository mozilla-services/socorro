/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

begin;

INSERT INTO addresses ( address )
VALUES ( 'Unknown' );

INSERT INTO domains ( domain )
VALUES ( 'Unknown' );

INSERT INTO os_names ( os_name, os_short_name )
VALUES ( 'Unknown', 'unk' );

INSERT INTO os_name_matches ( os_name, match_string )
VALUES ( 'Unknown', 'unknown' );

INSERT INTO os_versions ( os_name, major_version,
	minor_version, os_version_string )
VALUES ( 'Unknown', 0, 0, 'Unknown' );

INSERT INTO reasons ( reason )
VALUES ( 'Unknown' );

commit;