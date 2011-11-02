\set ON_ERROR_STOP 1

alter default privileges for role breakpad_rw grant select on sequences to breakpad;

alter default privileges for role breakpad_rw grant select on tables to breakpad;

grant select on all tables in schema public to breakpad;

grant select on all sequences in schema public to breakpad;

