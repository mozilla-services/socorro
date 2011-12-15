\set ON_ERROR_STOP 1

SELECT create_table_if_not_exists( 'socorro_db_version', $x$
CREATE TABLE socorro_db_version ( 
	current_version text primary key 
	);
	
INSERT INTO socorro_version VALUES ( '2.3.4' );

GRANT SELECT ON current_version TO breakpad;$x$,
'postgres');

SELECT create_table_if_not_exists( 'socorro_db_version_history', $x$
CREATE TABLE socorro_db_version_history (
	version text not null primary key,
	upgraded_on timestamptz not null default now(),
	backfill_to date
);

INSERT INTO socorro_db_version_history 
VALUES ( '2.3.4', '2011-12-13 12:00:00', NULL );

GRANT SELECT on socorro_version_history TO breakpad;$x$,
'postgres');

CREATE OR REPLACE FUNCTION update_socorro_db_version (
	newversion TEXT, backfilldate DATE default NULL )
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $f$
BEGIN
	UPDATE socorro_db_version SET current_version = newversion;
	
	INSERT INTO socorro_db_version_history ( version, upgraded_on, backfill_to )
	VALUES ( newversion, now(), backfilldate );
	
	RETURN true;
END; $f$;

	