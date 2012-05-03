-- analyst role, for read-only connections by analytics users
CREATE ROLE analyst;
ALTER ROLE analyst WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN CONNECTION LIMIT 10;
ALTER ROLE analyst SET statement_timeout TO '15min';
ALTER ROLE analyst SET work_mem TO '128MB';
ALTER ROLE analyst SET temp_buffers TO '128MB';

-- breakpad group and RW and RO users
-- these are our main users
CREATE ROLE breakpad;
ALTER ROLE breakpad WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB NOLOGIN;

CREATE ROLE breakpad_ro;
ALTER ROLE breakpad_ro WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN;
GRANT breakpad TO breakpad_ro GRANTED BY postgres;

CREATE ROLE breakpad_rw;
ALTER ROLE breakpad_rw WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN;
GRANT breakpad TO breakpad_rw GRANTED BY postgres;

-- breakpad_metrics user for nightly batch updates from metrics
CREATE ROLE breakpad_metrics;
ALTER ROLE breakpad_metrics WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN;
GRANT breakpad TO breakpad_metrics GRANTED BY postgres;

-- monitor and processor roles for data processing
CREATE ROLE processor;
ALTER ROLE processor WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN;
GRANT breakpad_rw TO processor GRANTED BY postgres;

CREATE ROLE monitor;
ALTER ROLE monitor WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN;
GRANT breakpad_rw TO monitor GRANTED BY postgres;
GRANT processor TO monitor GRANTED BY postgres;

-- monitoring group and separate users for ganglia and nagios
CREATE ROLE monitoring;
ALTER ROLE monitoring WITH SUPERUSER INHERIT NOCREATEROLE NOCREATEDB NOLOGIN;

CREATE ROLE ganglia;
ALTER ROLE ganglia WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN;
GRANT monitoring TO ganglia GRANTED BY postgres;

CREATE ROLE nagiosdaemon;
ALTER ROLE nagiosdaemon WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN;
GRANT monitoring TO nagiosdaemon GRANTED BY postgres;

-- replicator role for replication
CREATE ROLE replicator;
ALTER ROLE replicator WITH SUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN;

-- passwords.  reset here for specific passwords you need
-- only the roles needed on vagrant are given passwords here
-- so that other roles aren't automatically open

ALTER ROLE breakpad_ro WITH PASSWORD 'aPassword';
ALTER ROLE breakpad_rw WITH PASSWORD 'aPassword';
ALTER ROLE processor WITH PASSWORD 'aPassword';
ALTER ROLE monitor WITH PASSWORD 'aPassword';

