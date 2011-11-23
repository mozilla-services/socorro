begin;

INSERT INTO addresses ( address )
VALUES ( 'unknown' );

INSERT INTO domains ( domain )
VALUES ( 'unknown' );

INSERT INTO os_names ( os_name, os_short_name )
VALUES ( 'unknown', 'unk' );

INSERT INTO os_versions ( os_name, major_version,
	minor_version, os_version_string )
VALUES ( 'unknown', 0, 0, 'unknown' );

INSERT INTO reasons ( reason )
VALUES ( 'unknown' );

commit;