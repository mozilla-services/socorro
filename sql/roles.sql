/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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

WHILE iter <= array_upper(someroles, 1) LOOP
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

-- analyst role, for read-only connections by analytics users
ALTER ROLE analyst CONNECTION LIMIT 10;
ALTER ROLE analyst SET statement_timeout TO '15min';
ALTER ROLE analyst SET work_mem TO '128MB';
ALTER ROLE analyst SET temp_buffers TO '128MB';

-- breakpad group and RW and RO users
-- these are our main users
ALTER ROLE breakpad WITH NOLOGIN;
GRANT breakpad TO breakpad_ro GRANTED BY postgres;
GRANT breakpad TO breakpad_rw GRANTED BY postgres;

-- breakpad_metrics user for nightly batch updates from metrics
GRANT breakpad TO breakpad_metrics GRANTED BY postgres;

-- monitor and processor roles for data processing
GRANT breakpad_rw TO processor GRANTED BY postgres;
GRANT breakpad_rw TO monitor GRANTED BY postgres;
GRANT processor TO monitor GRANTED BY postgres;

-- monitoring group and separate users for ganglia and nagios
ALTER ROLE monitoring WITH NOLOGIN;
GRANT monitoring TO ganglia GRANTED BY postgres;
GRANT monitoring TO nagiosdaemon GRANTED BY postgres;

-- replicator role for replication
ALTER ROLE replicator WITH SUPERUSER;

