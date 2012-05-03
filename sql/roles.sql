-- this file creates all of the roles and inherited permissions
-- for socorro users on the PostgreSQL database.
-- it does NOT set passwords for them, which you need to do
-- separately.  Since it does set dummy passwords for a few
-- roles, if you are setting up Socorro on a non-test machine,
-- you will need to immediately reset those

-- create roles idempotently to avoid errors
-- also set dummy passwords for the core login roles
-- if we are creating them for the first time
DO $d$
DECLARE someroles TEXT[];
	rolepass TEXT[];
	iter INT := 1;
BEGIN

someroles := ARRAY['analyst','breakpad','breakpad_ro','breakpad_rw',
	'breakpad_metrics','processor','monitor','monitoring',
	'nagiosdaemon','ganglia','replicator'];
	
rolepass := ARRAY['breakpad_ro','breakpad_rw','processor','monitor'];

WHILE iter < array_upper(someroles, 1) LOOP
	PERFORM 1 FROM information_schema.enabled_roles
	WHERE role_name = someroles[iter];
	
	IF NOT FOUND THEN
		EXECUTE 'CREATE ROLE ' || someroles[iter] ||
			' WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN;';
		IF someroles[iter] = ANY ( rolepass ) THEN
			EXECUTE 'ALTER ROLE ' || someroles[iter] ||
				' WITH PASSWORD ''aPassword''';
		END IF;
	END IF;
	iter := iter + 1;
	
END LOOP;

END;$d$;

