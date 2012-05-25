\set ON_ERROR_STOP 1

CREATE OR REPLACE FUNCTION crontabber_timestamp ()
RETURNS trigger
LANGUAGE plpgsql
AS $f$
BEGIN
	
	NEW.last_updated = now();
	RETURN NEW;
	
END; $f$;

CREATE OR REPLACE FUNCTION crontabber_nodelete ()
RETURNS trigger
LANGUAGE plpgsql
AS $f$
BEGIN

	RAISE EXCEPTION 'you are not allowed to add or delete records from the crontabber table';

END;
$f$;

SELECT create_table_if_not_exists ( 'crontabber_state',
	$x$
	CREATE TABLE crontabber_state (
		state TEXT not null,
		last_updated timestamptz not null primary key
	);
	
	INSERT INTO crontabber_state VALUES ( '{}', now() );
	
	CREATE TRIGGER crontabber_timestamp BEFORE UPDATE ON crontabber_state
	FOR EACH ROW EXECUTE PROCEDURE crontabber_timestamp();
	
	CREATE TRIGGER crontabber_nodelete BEFORE INSERT OR DELETE ON crontabber_state
	FOR EACH ROW EXECUTE PROCEDURE crontabber_nodelete();	
	$x$,'breakpad_rw' );
	

DROP TABLE IF EXISTS cronjobs;