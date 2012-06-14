/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

BEGIN;

create table os_names (
    os_name text not null primary key
    );

alter table os_names OWNER TO breakpad_rw;

insert into os_names values ( 'Windows NT' ) , ( 'Linux' ), ('Mac OS X' ), ('Solaris');

-- this is a lookup list containing only the major OS names (OSX, Linux, Windows NT and Solaris).  It's there for convenience and does not change.

create table correlation_crash_counts (
    correlation_id SERIAL not null primary key,
    crash_day date not null,
    os_name citext not null references os_names(os_name),
    signature text not null,
	reason citext not null,
    crash_count integer not null,
    constraint correlation_crash_counts_key unique (crash_day, os_name, signature, reason)
);

alter table correlation_crash_counts OWNER TO breakpad_rw;

--This table contains the counts of crashes for that module/OS for that day. These rows are the same for both reports and are shared; as a result, attempts to insert duplicate rows will be silently ignored (trigger).

create table correlation_core_counts (
  correlation_id integer not null references correlation_crash_counts(correlation_id),
  processor_family citext not null,
  cores integer not null,
  crash_count integer not null,
  constraint correlation_core_count_key primary key (correlation_id, processor_family, cores)
);

alter table correlation_core_counts OWNER TO breakpad_rw;

--This is the table for storing the core_counts reports.

create table correlation_addons (
  correlation_id integer not null references correlation_crash_counts(correlation_id),
  libname text not null,
  addon_info citext,
  addon_url citext,
  addon_version text,
  crash_count integer not null,
  constraint correlation_addons_key primary key (correlation_id, libname, addon_version)
);

alter table correlation_addons OWNER TO breakpad_rw;

--This table populates both the interesting_addons and interesting_addons_with_versions reports.

create table correlation_modules (
  correlation_id integer not null references correlation_crash_counts(correlation_id),
  module_signature text not null,
  module_version text not null,
  module_info text,
  crash_count integer not null,
  constraint correlation_modules_key primary key (correlation_id, module_signature, module_version)
);

alter table correlation_modules OWNER TO breakpad_rw;

--This table populates both the interesting_modules and interesting_modules_with_versions reports.

create or replace function set_correlation_crash_count (
	n_date date,
	n_os_name citext,
	n_signature text,
	n_reason text,
	count integer )
RETURNS integer
LANGUAGE plpgsql
AS $f$
DECLARE new_id INT;
BEGIN
-- this function allows redundant addition of rows to correlation_crash_counts
-- because of the way that the reporting routines work.
-- it checks that nothing is NULL, and then returns the SERIAL ID
-- for either an existing or a new row

IF n_date IS NULL OR n_os_name IS NULL OR n_signature IS NULL
	OR n_reason IS NULL OR n_count IS NULL THEN
	RAISE EXCEPTION 'no correlation_crash_count field may be NULL';
END IF;

-- see if the row already exists
SELECT INTO new_id
	correlation_id
FROM correlation_crash_counts
WHERE date = n_date
	AND os_name = n_os_name
	AND signature = n_signature
	AND reason = n_reason;

IF new_id IS NULL THEN
	-- its a new correlation record, lets add it
	INSERT INTO correlation_crash_counts
		( date, os_name, signature, reason, crash_count )
	VALUES
		( n_date, n_os_name, n_signature, n_reason, n_crash_count );

	new_id := currval('correlation_crash_counts_correlation_id_seq');
END IF;

RETURN new_id;

END;$f$;

COMMIT;
