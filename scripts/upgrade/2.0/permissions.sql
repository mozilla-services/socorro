\set ON_ERROR_STOP 1

alter default privileges for role processor grant all on tables to breakpad_rw;
alter default privileges for role processor grant all on sequences to breakpad_rw;

alter default privileges for role monitor grant all on tables to breakpad_rw;
alter default privileges for role monitor grant all on sequences to breakpad_rw;

grant insert,update,delete,select on all tables in schema public to breakpad_rw;
grant usage,select,update on all sequences in schema public to breakpad_rw;


